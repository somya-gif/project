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
st.caption('E-commerce repeat purchase prediction · Sumit Gole')
if not (ROOT/'artifacts/metrics.json').exists():
    st.error('Run `python -m src.pipeline` first to generate the data.');st.stop()
if not (DATA/'customer_predictions.csv').exists():
    st.info('Run `python -m src.pipeline` once to download data and train the model, then restart.');st.stop()
metrics=json.loads((ROOT/'artifacts/metrics.json').read_text())
pred=read('customer_predictions.csv')
asof=str(pred.snapshot_date.iloc[0])[:10]
st.info(f'📅 Snapshot date: {asof} · UK giftware retailer · GBP')
page=st.sidebar.radio('Navigate',['Sales overview','Customer prediction','Retention cohorts','Campaign shortlist','Model evidence'])
st.sidebar.caption(f'Model: {metrics["selected_model"]} · Threshold: {metrics["threshold"]:.0%}')

if page=='Sales overview':
    d=read('daily_sales.csv');d['date']=pd.to_datetime(d.date)
    dates=st.date_input('Sales period',value=(d.date.min().date(),d.date.max().date()),min_value=d.date.min().date(),max_value=d.date.max().date())
    if len(dates)!=2: st.stop()
    d=d[d.date.between(pd.Timestamp(dates[0]),pd.Timestamp(dates[1]))]
    cols=st.columns(4)
    for c,label,value in zip(cols,['Gross Sales','Credits','Net Sales','Orders'],
        [f'£{d.gross_sales.sum():,.0f}',f'£{d.credits.sum():,.0f}',f'£{d.net_invoiced_sales.sum():,.0f}',f'{d.orders.sum():,.0f}']):c.metric(label,value)
    st.subheader('Sales trend')
    st.line_chart(d.set_index('date')[['gross_sales','net_invoiced_sales']])
    monthly=read('monthly_retention.csv')
    st.subheader('New vs returning customers')
    st.bar_chart(monthly.set_index('month')[['new_observed_customers','returning_customers']])

elif page=='Customer prediction':
    st.caption('Pick a customer to see their repeat-purchase probability and order history.')
    customer=st.selectbox('Customer ID',sorted(pred.customer_id.tolist()))
    r=pred.loc[pred.customer_id==customer].iloc[0]
    p=float(bundle()['model'].predict_proba(r[bundle()['features']].to_frame().T.astype(float))[0,1])
    a,b,c=st.columns(3)
    a.metric('30-day purchase probability',f'{p:.1%}')
    b.metric('Prediction','Likely to buy' if p>=metrics['threshold'] else 'Unlikely to buy')
    c.metric('Days since last order',f'{r.recency_days:.0f}')
    st.progress(p)
    st.subheader('Customer stats')
    st.dataframe(pd.DataFrame({'Metric':['Total orders','Total spend','Avg order value','Orders (last 30d)','Orders (last 90d)','Customer since (days)'],
        'Value':[str(int(r.orders_lifetime)),f'£{r.revenue_lifetime:,.2f}',f'£{r.average_order_value:,.2f}',str(int(r.orders_30d)),str(int(r.orders_90d)),str(round(r.tenure_days))]}),hide_index=True)
    history=read('known_customer_orders.csv');history=history[(history.customer_id==customer)&(history.order_date<asof)]
    if not history.empty:
        st.subheader('Order history')
        st.dataframe(history.sort_values('order_date',ascending=False),hide_index=True)

elif page=='Retention cohorts':
    d=read('cohort_retention.csv')
    st.subheader('How well do we retain customers?')
    st.caption('Each row is a cohort (grouped by first purchase month). Columns show what % came back in later months.')
    table=d.pivot(index='cohort',columns='month_index',values='retention_rate')
    st.dataframe(table.style.format('{:.0%}',na_rep='—').background_gradient(cmap='YlGnBu',vmin=0,vmax=1),height=650)
    monthly=read('monthly_retention.csv')
    st.subheader('Monthly trends')
    st.line_chart(monthly.set_index('month')[['monthly_retention_rate','returning_customer_share']])

elif page=='Campaign shortlist':
    st.subheader('Build a target audience')
    st.caption('Filter customers by likelihood and spend, then download the list.')
    band=st.multiselect('Purchase likelihood', ['Low','Medium','High'],default=['High'])
    spend=st.number_input('Minimum lifetime spend (£)',min_value=0.,value=0.)
    selected=pred[pred.likelihood_band.isin(band)&(pred.revenue_lifetime>=spend)].sort_values('probability',ascending=False)
    upload=st.file_uploader('Or upload a CSV with customer_id column to look up specific customers',type=['csv'])
    if upload:
        try:
            if upload.size>2_000_000: raise ValueError('File must be below 2 MB.')
            ids=pd.read_csv(upload,dtype=str)
            if 'customer_id' not in ids: raise ValueError('Need a customer_id column.')
            ids['customer_id']=ids.customer_id.str.strip()
            selected=ids[['customer_id']].drop_duplicates().merge(pred,on='customer_id',how='left',validate='one_to_one')
            missing=selected.probability.isna().sum()
            if missing: st.warning(f'{missing} IDs not found in the dataset.')
        except (ValueError,pd.errors.ParserError,UnicodeDecodeError) as e:
            st.error(str(e));st.stop()
    st.metric('Customers in audience',len(selected))
    st.dataframe(selected[['customer_id','probability','predicted_repeat','likelihood_band','recency_days','orders_lifetime','revenue_lifetime']],hide_index=True)
    st.download_button('⬇️ Download CSV',selected.to_csv(index=False),'retention_audience.csv','text/csv')

else:
    st.subheader('How good is the model?')
    st.caption('These results are from a held-out test set the model never saw during training.')
    m=metrics['test'];a,b,c,d=st.columns(4)
    a.metric('Average precision',f'{m["average_precision"]:.3f}')
    b.metric('Base rate',f'{m["prevalence"]:.1%}')
    c.metric('Top 10% lift',f'{m["lift_at_top_10pct"]:.2f}×')
    d.metric('Brier score',f'{m["brier_score"]:.3f}')
    st.json({'selection':metrics['selection_metric'],'threshold_policy':metrics['threshold_policy'],'time_splits':metrics['splits']})
    st.subheader('Model comparison')
    st.dataframe(pd.DataFrame(metrics['validation_candidates']).drop(columns='confusion_matrix_tn_fp_fn_tp'),hide_index=True)
    st.subheader('Monthly test performance')
    st.dataframe(read('model_performance.csv'),hide_index=True)
    st.subheader('Are the probabilities reliable?')
    st.dataframe(read('calibration.csv'),hide_index=True)
    st.subheader('Which features matter most?')
    st.bar_chart(read('feature_importance.csv').set_index('feature')['ap_decrease'])
    st.json(json.loads((ROOT/'artifacts/data_quality.json').read_text()))
