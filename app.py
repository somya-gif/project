"""Retention Lens — historical portfolio demo, not a live customer scoring service."""
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
    # Only load the trusted project artifact; user uploads are never unpickled.
    return joblib.load(ROOT/'artifacts/model.joblib')

st.title('Retention Lens')
st.caption('E-commerce intelligence · 30-day repeat purchase · Sumit Gole')
if not (ROOT/'artifacts/metrics.json').exists():
    st.error('Run python -m src.pipeline from the project directory first.');st.stop()
if not (DATA/'customer_predictions.csv').exists():
    st.info('Customer-level data is generated locally, not published in this repository. Run python -m src.pipeline once, then restart this app.');st.stop()
metrics=json.loads((ROOT/'artifacts/metrics.json').read_text())
pred=read('customer_predictions.csv')
asof=str(pred.snapshot_date.iloc[0])[:10]
st.info(f'Historical demo • Snapshot {asof} • UK giftware, GBP • These are not predictions for today. No purchase within 30 days does not mean permanent churn.')
page=st.sidebar.radio('Workspace',['Sales overview','Customer prediction','Retention cohorts','Campaign shortlist','Model evidence'])
st.sidebar.caption(f'Model: {metrics["selected_model"]} · Threshold: {metrics["threshold"]:.0%}')
st.sidebar.caption('Probabilities estimate purchase behaviour, not the effect of sending a discount.')

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
    st.caption('Includes anonymous invoices. Credits are booked on their own date; this is not profit. Final source day is partial.')
    monthly=read('monthly_retention.csv')
    st.subheader('Customer mix · complete months')
    st.bar_chart(monthly.set_index('month')[['new_observed_customers','returning_customers']])
    st.caption('Customer mix shows the full history independently of the sales date filter.')

elif page=='Customer prediction':
    customer=st.selectbox('Existing customer ID',sorted(pred.customer_id.tolist()))
    r=pred.loc[pred.customer_id==customer].iloc[0]
    p=float(bundle()['model'].predict_proba(r[bundle()['features']].to_frame().T.astype(float))[0,1])
    a,b,c=st.columns(3)
    a.metric('Purchase in next 30 days',f'{p:.1%}')
    b.metric('Threshold decision','Likely repeat' if p>=metrics['threshold'] else 'Below repeat threshold')
    c.metric('Days since last order',f'{r.recency_days:.0f}')
    st.progress(p)
    st.caption(f'Outcome window: {asof} inclusive to {(pd.Timestamp(asof)+pd.Timedelta(days=30)).date()} exclusive. Outcomes for this demo window are unavailable.')
    st.subheader('Observed purchase behaviour')
    st.dataframe(pd.DataFrame({'Metric':['Orders observed','Total invoiced spend','Average order','Orders in last 30 days','Orders in last 90 days','Observed tenure (days)'],
        'Value':[str(int(r.orders_lifetime)),f'£{r.revenue_lifetime:,.2f}',f'£{r.average_order_value:,.2f}',str(int(r.orders_30d)),str(int(r.orders_90d)),str(round(r.tenure_days))]}),hide_index=True)
    history=read('known_customer_orders.csv');history=history[(history.customer_id==customer)&(history.order_date<asof)]
    st.dataframe(history.sort_values('order_date',ascending=False),hide_index=True)
    st.caption('These are observed features, not causal or customer-level model explanations. Global model sensitivity is available in Model evidence.')

elif page=='Retention cohorts':
    d=read('cohort_retention.csv')
    st.subheader('First-observed-purchase cohorts')
    table=d.pivot(index='cohort',columns='month_index',values='retention_rate')
    st.dataframe(table.style.format('{:.0%}',na_rep='Not observed').background_gradient(cmap='YlGnBu',vmin=0,vmax=1),height=650)
    st.caption('Denominator: customers first observed buying in the cohort month. Numerator: those customers buying in each later month. Re-entry is allowed. Incomplete/future months remain blank; observed zero-purchase months are zero. Dataset start is not necessarily customer acquisition.')
    monthly=read('monthly_retention.csv')
    st.line_chart(monthly.set_index('month')[['monthly_retention_rate','returning_customer_share']])

elif page=='Campaign shortlist':
    st.subheader('Explore a customer audience')
    band=st.multiselect('Purchase likelihood', ['Low','Medium','High'],default=['High'])
    spend=st.number_input('Minimum observed spend (£)',min_value=0.,value=0.)
    selected=pred[pred.likelihood_band.isin(band)&(pred.revenue_lifetime>=spend)].sort_values('probability',ascending=False)
    upload=st.file_uploader('Optional CSV with customer_id column to score known IDs',type=['csv'])
    if upload:
        try:
            if upload.size>2_000_000: raise ValueError('File must be below 2 MB.')
            ids=pd.read_csv(upload,dtype=str)
            if 'customer_id' not in ids: raise ValueError('Required column: customer_id')
            ids['customer_id']=ids.customer_id.str.strip()
            selected=ids[['customer_id']].drop_duplicates().merge(pred,on='customer_id',how='left',validate='one_to_one')
            missing=selected.probability.isna().sum()
            if missing: st.warning(f'{missing} unknown/blank IDs have no prediction. They are not treated as zero probability.')
            st.caption('Uploaded IDs override the audience filters; these are cached snapshot scores, not predictions on new transactions.')
        except (ValueError,pd.errors.ParserError,UnicodeDecodeError) as e:
            st.error(str(e));st.stop()
    st.metric('Rows in audience',len(selected))
    st.dataframe(selected[['customer_id','probability','predicted_repeat','likelihood_band','recency_days','orders_lifetime','revenue_lifetime']],hide_index=True)
    st.download_button('Download audience CSV',selected.to_csv(index=False),'retention_audience.csv','text/csv')
    st.warning('Likelihood bands are descriptive (Low ≤20%, Medium >20–50%, High >50%). Low likelihood is not proof of churn. Do not infer discount uplift or revenue gains without a randomized campaign test.')

else:
    st.subheader('Held-out future-period evaluation')
    m=metrics['test'];a,b,c,d=st.columns(4)
    a.metric('Average precision',f'{m["average_precision"]:.3f}')
    b.metric('Base rate',f'{m["prevalence"]:.1%}')
    c.metric('Top 10% lift',f'{m["lift_at_top_10pct"]:.2f}×')
    d.metric('Brier score',f'{m["brier_score"]:.3f}')
    st.json({'selection':metrics['selection_metric'],'threshold_policy':metrics['threshold_policy'],'time_splits':metrics['splits']})
    st.dataframe(pd.DataFrame(metrics['validation_candidates']).drop(columns='confusion_matrix_tn_fp_fn_tp'),hide_index=True)
    st.subheader('Test performance by snapshot')
    st.dataframe(read('model_performance.csv'),hide_index=True)
    st.subheader('Probability reliability on test')
    st.dataframe(read('calibration.csv'),hide_index=True)
    st.subheader('Global validation feature sensitivity')
    st.bar_chart(read('feature_importance.csv').set_index('feature')['ap_decrease'])
    st.caption('Permutation importance measures average-precision loss after shuffling a feature. Correlated features can dilute importance. Probabilities were not separately calibrated. Repeated customers are expected for an existing-customer deployment; snapshot rows are not independent people.')
    st.json(json.loads((ROOT/'artifacts/data_quality.json').read_text()))
