"""Retention Lens — e-commerce repeat purchase prediction demo."""
from pathlib import Path
import json
import joblib
import pandas as pd
import streamlit as st

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/processed'
st.set_page_config(page_title='Retention Lens | Sumit Gole',page_icon='↻',layout='wide')

@st.cache_data
def read(name):
    return pd.read_csv(DATA/name,dtype={'customer_id':str},float_precision='round_trip')

@st.cache_resource
def bundle():
    return joblib.load(ROOT/'artifacts/model.joblib')

st.title('Retention Lens')
st.caption('E-commerce intelligence · 30-day repeat purchase · Sumit Gole')
if not (ROOT/'artifacts/metrics.json').exists():
    st.error('Run python -m src.pipeline from the project directory first.');st.stop()
if not (DATA/'customer_predictions.csv').exists():
    st.info('Run python -m src.pipeline once to generate data, then restart.');st.stop()
metrics=json.loads((ROOT/'artifacts/metrics.json').read_text())
pred=read('customer_predictions.csv')
asof=str(pred.snapshot_date.iloc[0])[:10]
st.info(f'Historical snapshot from {asof} · UK giftware retailer · GBP')
page=st.sidebar.radio('Workspace',['Sales overview','Customer prediction','Retention cohorts','Campaign shortlist','Model evidence'])
st.sidebar.caption(f'Model: {metrics["selected_model"]} · Threshold: {metrics["threshold"]:.0%}')

if page=='Sales overview':
    d=read('daily_sales.csv');d['date']=pd.to_datetime(d.date)
    dates=st.date_input('Sales period',value=(d.date.min().date(),d.date.max().date()),min_value=d.date.min().date(),max_value=d.date.max().date())
    if len(dates)!=2: st.stop()
    d=d[d.date.between(pd.Timestamp(dates[0]),pd.Timestamp(dates[1]))]
    cols=st.columns(4)
    for c,label,value in zip(cols,['Gross invoiced sales','Credits','Net invoiced sales','Orders'],
        [f'£{d.gross_sales.sum():,.0f}',f'£{d.credits.sum():,.0f}',f'£{d.net_invoiced_sales.sum():,.0f}',f'{d.orders.sum():,.0f}']):c.metric(label,value)
    st.subheader('Sales trend')
    st.line_chart(d.set_index('date')[['gross_sales','net_invoiced_sales']])
    monthly=read('monthly_retention.csv')
    st.subheader('Customer mix · complete months')
    st.bar_chart(monthly.set_index('month')[['new_observed_customers','returning_customers']])

elif page=='Customer prediction':
    customer=st.selectbox('Existing customer ID',sorted(pred.customer_id.tolist()))
    r=pred.loc[pred.customer_id==customer].iloc[0]
    p=float(bundle()['model'].predict_proba(r[bundle()['features']].to_frame().T.astype(float))[0,1])
    a,b,c=st.columns(3)
    a.metric('Purchase in next 30 days',f'{p:.1%}')
    b.metric('Threshold decision','Likely repeat' if p>=metrics['threshold'] else 'Below threshold')
    c.metric('Days since last order',f'{r.recency_days:.0f}')
    st.progress(p)
    st.subheader('Purchase history')
    st.dataframe(pd.DataFrame({'Metric':['Orders observed','Total spend','Avg order value','Orders (30d)','Orders (90d)','Tenure (days)'],
        'Value':[str(int(r.orders_lifetime)),f'£{r.revenue_lifetime:,.2f}',f'£{r.average_order_value:,.2f}',str(int(r.orders_30d)),str(int(r.orders_90d)),str(round(r.tenure_days))]}),hide_index=True)
    history=read('known_customer_orders.csv');history=history[(history.customer_id==customer)&(history.order_date<asof)]
    st.dataframe(history.sort_values('order_date',ascending=False),hide_index=True)

elif page=='Retention cohorts':
    d=read('cohort_retention.csv')
    st.subheader('First-purchase cohorts')
    table=d.pivot(index='cohort',columns='month_index',values='retention_rate')
    st.dataframe(table.style.format('{:.0%}',na_rep='—').background_gradient(cmap='YlGnBu',vmin=0,vmax=1),height=650)
    monthly=read('monthly_retention.csv')
    st.line_chart(monthly.set_index('month')[['monthly_retention_rate','returning_customer_share']])

elif page=='Campaign shortlist':
    st.subheader('Build an audience')
    band=st.multiselect('Purchase likelihood', ['Low','Medium','High'],default=['High'])
    spend=st.number_input('Minimum observed spend (£)',min_value=0.,value=0.)
    selected=pred[pred.likelihood_band.isin(band)&(pred.revenue_lifetime>=spend)].sort_values('probability',ascending=False)
    upload=st.file_uploader('Upload CSV with customer_id column to look up scores',type=['csv'])
    if upload:
        try:
            if upload.size>2_000_000: raise ValueError('File must be below 2 MB.')
            ids=pd.read_csv(upload,dtype=str)
            if 'customer_id' not in ids: raise ValueError('Required column: customer_id')
            ids['customer_id']=ids.customer_id.str.strip()
            selected=ids[['customer_id']].drop_duplicates().merge(pred,on='customer_id',how='left',validate='one_to_one')
            missing=selected.probability.isna().sum()
            if missing: st.warning(f'{missing} IDs not found in the dataset.')
        except (ValueError,pd.errors.ParserError,UnicodeDecodeError) as e:
            st.error(str(e));st.stop()
    st.metric('Rows in audience',len(selected))
    st.dataframe(selected[['customer_id','probability','predicted_repeat','likelihood_band','recency_days','orders_lifetime','revenue_lifetime']],hide_index=True)
    st.download_button('Download audience CSV',selected.to_csv(index=False),'retention_audience.csv','text/csv')

else:
    st.subheader('Held-out test evaluation')
    m=metrics['test'];a,b,c,d=st.columns(4)
    a.metric('Average precision',f'{m["average_precision"]:.3f}')
    b.metric('Base rate',f'{m["prevalence"]:.1%}')
    c.metric('Top 10% lift',f'{m["lift_at_top_10pct"]:.2f}×')
    d.metric('Brier score',f'{m["brier_score"]:.3f}')
    st.json({'selection':metrics['selection_metric'],'threshold_policy':metrics['threshold_policy'],'time_splits':metrics['splits']})
    st.dataframe(pd.DataFrame(metrics['validation_candidates']).drop(columns='confusion_matrix_tn_fp_fn_tp'),hide_index=True)
    st.subheader('Test performance by snapshot')
    st.dataframe(read('model_performance.csv'),hide_index=True)
    st.subheader('Probability reliability')
    st.dataframe(read('calibration.csv'),hide_index=True)
    st.subheader('Feature importance (permutation)')
    st.bar_chart(read('feature_importance.csv').set_index('feature')['ap_decrease'])
    st.json(json.loads((ROOT/'artifacts/data_quality.json').read_text()))
