"""
Feature engineering and data cleaning for repeat purchase prediction.
"""

from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd

# Core behavioural features used by the model
FEATURES = [
    'recency_days',
    'tenure_days',
    'orders_lifetime',
    'revenue_lifetime',
    'average_order_value',
    'orders_30d',
    'orders_90d',
    'revenue_90d',
    'mean_gap_days',
    'active_months',
    'is_uk',
]


def snapshot(
    orders: pd.DataFrame,
    cutoff: str,
    with_label: bool = False,
    observation_end: str = None,
) -> pd.DataFrame:
    """
    Computes point-in-time RFM and tenure features for all customers who made
    at least one purchase strictly before the given cutoff date.
    
    If with_label=True, looks forward 30 days to see if the customer bought again.
    """
    cutoff = pd.Timestamp(cutoff)
    end = cutoff + pd.Timedelta(days=30)

    if with_label and (observation_end is None or end > pd.Timestamp(observation_end)):
        raise ValueError('Full 30-day outcome window required to avoid censored labels.')

    # Filter orders strictly before the cutoff to prevent data leakage
    history = orders.loc[orders.order_date < cutoff].sort_values(['order_date', 'order_id'])
    if history.empty:
        raise ValueError('No existing customers before this cutoff date.')

    # Aggregate customer order history
    grouped = history.groupby('customer_id')
    features = grouped.agg(
        first=('order_date', 'min'),
        last=('order_date', 'max'),
        orders_lifetime=('order_id', 'nunique'),
        revenue_lifetime=('revenue', 'sum'),
        average_order_value=('revenue', 'mean'),
        country=('country', 'last'),
    )

    # Days since last order & days since first order
    features['recency_days'] = (cutoff - features['last']).dt.total_seconds() / 86400
    features['tenure_days'] = (cutoff - features['first']).dt.total_seconds() / 86400

    # Average days between orders (-1 for single-order customers as a sentinel)
    span_days = (features['last'] - features['first']).dt.total_seconds() / 86400
    gaps = features.orders_lifetime - 1
    features['mean_gap_days'] = (span_days / gaps.replace(0, np.nan)).fillna(-1)

    # Number of distinct calendar months with activity
    features['active_months'] = (
        history.assign(month=history.order_date.dt.to_period('M'))
        .groupby('customer_id')
        .month.nunique()
    )

    # Recent activity windows (last 30 and 90 days)
    for days in [30, 90]:
        recent = history[history.order_date >= cutoff - pd.Timedelta(days=days)].groupby('customer_id')
        features[f'orders_{days}d'] = recent.order_id.nunique().reindex(features.index, fill_value=0)
        if days == 90:
            features['revenue_90d'] = recent.revenue.sum().reindex(features.index, fill_value=0)

    # Geographic indicator
    features['is_uk'] = (features.country == 'United Kingdom').astype(int)
    features['snapshot_date'] = cutoff

    # Target: 1 if customer ordered in [cutoff, cutoff + 30 days), else 0
    if with_label:
        buyers = orders.loc[
            (orders.order_date >= cutoff) & (orders.order_date < end),
            'customer_id',
        ]
        features['target'] = features.index.isin(buyers).astype(int)

    return features.reset_index().drop(columns=['first', 'last'])


def quality_and_clean(raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Cleans raw UCI Online Retail II transactions:
    - Normalizes column names
    - Removes exact duplicate rows
    - Separates positive purchases from cancellations/credits
    - Retains anonymous orders for financial reconciliation
    """
    df = raw.rename(columns={
        'Invoice': 'order_id',
        'StockCode': 'product_id',
        'Description': 'description',
        'Quantity': 'quantity',
        'InvoiceDate': 'order_date',
        'Price': 'unit_price',
        'Customer ID': 'customer_id',
        'Country': 'country',
    }).copy()

    required_cols = {'order_id', 'product_id', 'quantity', 'order_date', 'unit_price', 'customer_id', 'country'}
    if not required_cols.issubset(df):
        raise ValueError(f'Missing columns in input: {required_cols - set(df)}')

    audit = {
        'input_rows': len(df),
        'exact_duplicate_rows': int(df.duplicated().sum()),
    }
    df = df.drop_duplicates().copy()

    df['order_date'] = pd.to_datetime(df.order_date, errors='coerce')
    for col in ['quantity', 'unit_price']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['customer_id'] = pd.to_numeric(df.customer_id, errors='coerce').astype('Int64').astype('string')
    df['country'] = df.country.fillna('Unknown')
    df['order_id'] = df.order_id.astype(str)
    df['product_id'] = df.product_id.astype(str)

    audit['missing_customer_rows'] = int(df.customer_id.isna().sum())

    valid_rows = df.order_date.notna() & np.isfinite(df.quantity) & np.isfinite(df.unit_price) & (df.unit_price > 0)
    cancelled = df.order_id.str.upper().str.startswith('C')

    purchases = df.loc[valid_rows & (df.quantity > 0) & ~cancelled].copy()
    credits = df.loc[valid_rows & (df.quantity < 0)].copy()

    purchases['revenue'] = purchases.quantity * purchases.unit_price
    credits['credit_amount'] = -credits.quantity * credits.unit_price

    audit.update(
        purchase_lines=len(purchases),
        credit_lines=len(credits),
        excluded_other_rows=len(df) - len(purchases) - len(credits),
        anonymous_purchase_lines=int(purchases.customer_id.isna().sum()),
        gross_sales_gbp=float(purchases.revenue.sum()),
        credits_gbp=float(credits.credit_amount.sum()),
        min_timestamp=str(df.order_date.min()),
        max_timestamp=str(df.order_date.max()),
    )

    if purchases.groupby('order_id').customer_id.nunique().gt(1).any():
        raise ValueError('Invoice unexpectedly maps to multiple customer IDs')

    known = purchases.dropna(subset=['customer_id'])
    orders = known.groupby(['customer_id', 'order_id'], as_index=False).agg(
        order_date=('order_date', 'min'),
        revenue=('revenue', 'sum'),
        country=('country', 'first'),
    )

    return purchases, credits, orders, audit
