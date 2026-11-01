"""
Retention Lens — E-commerce repeat purchase prediction web app.
Built by Soumya Prakash Patel.
"""

from pathlib import Path
import json
import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data/processed'

st.set_page_config(page_title='Retention Lens | Soumya Prakash Patel', page_icon='↻', layout='wide')


@st.cache_data
def read_table(filename: str):
    return pd.read_csv(DATA / filename, dtype={'customer_id': str}, float_precision='round_trip')


@st.cache_resource
def load_model_bundle():
    return joblib.load(ROOT / 'artifacts/model.joblib')


# App Header
st.title('Retention Lens 🔁')
st.caption('Customer Repeat Purchase Prediction System · Soumya Prakash Patel')

if not (ROOT / 'artifacts/metrics.json').exists():
    st.error("Please run 'python -m src.pipeline' first to create the model artifacts.")
    st.stop()

if not (DATA / 'customer_predictions.csv').exists():
    st.info("Please run 'python -m src.pipeline' once to download data and train the model.")
    st.stop()

metrics = json.loads((ROOT / 'artifacts/metrics.json').read_text())
predictions_df = read_table('customer_predictions.csv')
snapshot_date = str(predictions_df.snapshot_date.iloc[0])[:10]

st.info(f'📅 Snapshot Date: {snapshot_date} · Store: UK Giftware Retailer · Currency: GBP (£)')

page = st.sidebar.radio('Go to page:', [
    'Sales overview',
    'Customer prediction',
    'Retention cohorts',
    'Campaign shortlist',
    'Model evidence',
])
st.sidebar.caption(f"Model: {metrics['selected_model']} · Decision Threshold: {metrics['threshold']:.0%}")


# Page 1: Sales Overview
if page == 'Sales overview':
    sales_df = read_table('daily_sales.csv')
    sales_df['date'] = pd.to_datetime(sales_df.date)

    selected_dates = st.date_input(
        'Select Date Range:',
        value=(sales_df.date.min().date(), sales_df.date.max().date()),
        min_value=sales_df.date.min().date(),
        max_value=sales_df.date.max().date(),
    )
    if len(selected_dates) != 2:
        st.stop()

    filtered_sales = sales_df[sales_df.date.between(pd.Timestamp(selected_dates[0]), pd.Timestamp(selected_dates[1]))]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Gross Sales', f"£{filtered_sales.gross_sales.sum():,.0f}")
    c2.metric('Returns & Credits', f"£{filtered_sales.credits.sum():,.0f}")
    c3.metric('Net Sales', f"£{filtered_sales.net_invoiced_sales.sum():,.0f}")
    c4.metric('Total Orders', f"{filtered_sales.orders.sum():,.0f}")

    st.subheader('Daily Sales Trend')
    st.line_chart(filtered_sales.set_index('date')[['gross_sales', 'net_invoiced_sales']])

    monthly_retention = read_table('monthly_retention.csv')
    st.subheader('New vs. Returning Customers (By Month)')
    st.bar_chart(monthly_retention.set_index('month')[['new_observed_customers', 'returning_customers']])


# Page 2: Customer Prediction
elif page == 'Customer prediction':
    st.caption('Select a customer to see their repeat purchase probability and order history.')

    customer_id = st.selectbox('Choose Customer ID:', sorted(predictions_df.customer_id.tolist()))
    customer_row = predictions_df.loc[predictions_df.customer_id == customer_id].iloc[0]

    model_bundle = load_model_bundle()
    features_input = customer_row[model_bundle['features']].to_frame().T.astype(float)
    prob = float(model_bundle['model'].predict_proba(features_input)[0, 1])

    c1, c2, c3 = st.columns(3)
    c1.metric('30-Day Buy Probability', f'{prob:.1%}')
    c2.metric('Decision', 'Likely to buy' if prob >= metrics['threshold'] else 'Unlikely to buy')
    c3.metric('Days Since Last Order', f'{customer_row.recency_days:.0f} days')
    st.progress(prob)

    st.subheader('Customer Summary')
    stats_df = pd.DataFrame({
        'Question': [
            'How many total orders have they placed?',
            'How much total money have they spent?',
            'What is their average spend per order?',
            'How many orders in the last 30 days?',
            'How many orders in the last 90 days?',
            'How many days since their first purchase?',
        ],
        'Value': [
            f"{int(customer_row.orders_lifetime)} orders",
            f"£{customer_row.revenue_lifetime:,.2f}",
            f"£{customer_row.average_order_value:,.2f}",
            f"{int(customer_row.orders_30d)} orders",
            f"{int(customer_row.orders_90d)} orders",
            f"{round(customer_row.tenure_days)} days",
        ],
    })
    st.dataframe(stats_df, hide_index=True)

    orders_history = read_table('known_customer_orders.csv')
    customer_history = orders_history[
        (orders_history.customer_id == customer_id) & (orders_history.order_date < snapshot_date)
    ]
    if not customer_history.empty:
        st.subheader('Past Order History')
        st.dataframe(customer_history.sort_values('order_date', ascending=False), hide_index=True)


# Page 3: Retention Cohorts
elif page == 'Retention cohorts':
    st.subheader('How Well Do We Keep Customers Coming Back?')
    st.caption('Each row is a group of customers who first bought in that month. The columns show what percentage returned in later months.')

    cohort_df = read_table('cohort_retention.csv')
    cohort_matrix = cohort_df.pivot(index='cohort', columns='month_index', values='retention_rate')
    st.dataframe(
        cohort_matrix.style.format('{:.0%}', na_rep='—').background_gradient(cmap='YlGnBu', vmin=0, vmax=1),
        height=600,
    )

    monthly_trends = read_table('monthly_retention.csv')
    st.subheader('Overall Monthly Retention Trends')
    st.line_chart(monthly_trends.set_index('month')[['monthly_retention_rate', 'returning_customer_share']])


# Page 4: Campaign Shortlist
elif page == 'Campaign shortlist':
    st.subheader('Find Customers for a Marketing Campaign')
    st.caption('Filter customers by purchase likelihood and minimum spending, then download the list as a CSV.')

    chosen_bands = st.multiselect('Purchase Likelihood Band:', ['Low', 'Medium', 'High'], default=['High'])
    min_spend = st.number_input('Minimum Lifetime Spend (£):', min_value=0.0, value=0.0)

    selected_audience = predictions_df[
        predictions_df.likelihood_band.isin(chosen_bands) & (predictions_df.revenue_lifetime >= min_spend)
    ].sort_values('probability', ascending=False)

    uploaded_file = st.file_uploader('Or upload a CSV with a customer_id column to check specific customers:', type=['csv'])
    if uploaded_file:
        try:
            if uploaded_file.size > 2_000_000:
                raise ValueError('Uploaded file must be smaller than 2 MB.')
            uploaded_ids = pd.read_csv(uploaded_file, dtype=str)
            if 'customer_id' not in uploaded_ids:
                raise ValueError("The uploaded CSV must have a column named 'customer_id'.")
            uploaded_ids['customer_id'] = uploaded_ids.customer_id.str.strip()
            selected_audience = uploaded_ids[['customer_id']].drop_duplicates().merge(
                predictions_df, on='customer_id', how='left', validate='one_to_one'
            )
            unfound = selected_audience.probability.isna().sum()
            if unfound:
                st.warning(f"{unfound} customer IDs were not found in our store database.")
        except Exception as err:
            st.error(f'Error reading file: {err}')
            st.stop()

    st.metric('Customers in this Audience', len(selected_audience))
    st.dataframe(
        selected_audience[['customer_id', 'probability', 'predicted_repeat', 'likelihood_band', 'recency_days', 'orders_lifetime', 'revenue_lifetime']],
        hide_index=True,
    )
    st.download_button(
        '⬇️ Download Audience CSV',
        selected_audience.to_csv(index=False),
        'customer_campaign_audience.csv',
        'text/csv',
    )


# Page 5: Model Evidence
else:
    st.subheader('How Accurate is the Model?')
    st.caption('These scores were measured on completely unseen future test data that the model never saw during training.')

    test_metrics = metrics['test']
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Average Precision', f"{test_metrics['average_precision']:.3f}", help='Measures how well the model ranks buyers ahead of non-buyers')
    c2.metric('Baseline Rate', f"{test_metrics['prevalence']:.1%}", help='Percentage of normal customers who bought again')
    c3.metric('Top 10% Lift', f"{test_metrics['lift_at_top_10pct']:.2f}×", help='How much more likely the top 10% customers are to buy compared to average')
    c4.metric('Brier Score (Error)', f"{test_metrics['brier_score']:.3f}", help='Measures probability error (lower is better)')

    st.subheader('Candidate Models Compared')
    st.caption('We trained 3 candidate algorithms on past data. Gradient Boosting performed the best on validation tests:')
    candidates_df = pd.DataFrame(metrics['validation_candidates']).drop(columns='confusion_matrix_tn_fp_fn_tp')
    st.dataframe(candidates_df, hide_index=True)

    st.subheader('Performance Across Different Test Months')
    st.dataframe(read_table('model_performance.csv'), hide_index=True)

    st.subheader('Which Customer Signals Matter Most?')
    st.caption('Shows how much accuracy drops when each feature is shuffled. High bars mean the feature is very important.')
    feature_importance_df = read_table('feature_importance.csv')
    st.bar_chart(feature_importance_df.set_index('feature')['ap_decrease'])
