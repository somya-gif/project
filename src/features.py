"""Point-in-time features. All intervals use [start, end)."""
import numpy as np
import pandas as pd

FEATURES = ['recency_days', 'tenure_days', 'orders_lifetime', 'revenue_lifetime',
            'average_order_value', 'orders_30d', 'orders_90d', 'revenue_90d',
            'mean_gap_days', 'active_months', 'is_uk']

def snapshot(orders, cutoff, with_label=False, observation_end=None):
    cutoff = pd.Timestamp(cutoff)
    end = cutoff + pd.Timedelta(days=30)
    if with_label and (observation_end is None or end > pd.Timestamp(observation_end)):
        raise ValueError('Full 30-day outcome window is required; do not label censored customers.')
    h = orders.loc[orders.order_date < cutoff].sort_values(['order_date', 'order_id'])
    if h.empty:
        raise ValueError('No existing customers before this cutoff.')
    g = h.groupby('customer_id')
    f = g.agg(first=('order_date','min'), last=('order_date','max'),
              orders_lifetime=('order_id','nunique'), revenue_lifetime=('revenue','sum'),
              average_order_value=('revenue','mean'), country=('country','last'))
    f['recency_days'] = (cutoff-f['last']).dt.total_seconds()/86400
    f['tenure_days'] = (cutoff-f['first']).dt.total_seconds()/86400
    f['mean_gap_days'] = ((f['last']-f['first']).dt.total_seconds()/86400 / (f.orders_lifetime-1).replace(0,np.nan)).fillna(-1)
    f['active_months'] = h.assign(month=h.order_date.dt.to_period('M')).groupby('customer_id').month.nunique()
    for days in [30,90]:
        r = h[h.order_date >= cutoff-pd.Timedelta(days=days)].groupby('customer_id')
        f[f'orders_{days}d'] = r.order_id.nunique().reindex(f.index,fill_value=0)
        if days == 90:
            f['revenue_90d'] = r.revenue.sum().reindex(f.index,fill_value=0)
    f['is_uk'] = (f.country == 'United Kingdom').astype(int)
    f['snapshot_date'] = cutoff
    if with_label:
        buyers = orders.loc[(orders.order_date >= cutoff)&(orders.order_date < end),'customer_id']
        f['target'] = f.index.isin(buyers).astype(int)
    return f.reset_index().drop(columns=['first','last'])

def quality_and_clean(raw):
    d=raw.rename(columns={'Invoice':'order_id','StockCode':'product_id','Description':'description',
        'Quantity':'quantity','InvoiceDate':'order_date','Price':'unit_price','Customer ID':'customer_id','Country':'country'}).copy()
    required={'order_id','product_id','quantity','order_date','unit_price','customer_id','country'}
    if not required.issubset(d): raise ValueError(f'Missing columns: {required-set(d)}')
    audit={'input_rows':len(d), 'exact_duplicate_rows':int(d.duplicated().sum())}
    d=d.drop_duplicates().copy()
    d['order_date']=pd.to_datetime(d.order_date,errors='coerce')
    for col in ['quantity','unit_price']: d[col]=pd.to_numeric(d[col],errors='coerce')
    d['customer_id']=pd.to_numeric(d.customer_id,errors='coerce').astype('Int64').astype('string')
    d['country']=d.country.fillna('Unknown')
    d['order_id']=d.order_id.astype(str)
    d['product_id']=d.product_id.astype(str)
    audit['missing_customer_rows']=int(d.customer_id.isna().sum())
    valid=d.order_date.notna() & np.isfinite(d.quantity) & np.isfinite(d.unit_price) & (d.unit_price>0)
    cancelled=d.order_id.str.upper().str.startswith('C')
    purchases=d.loc[valid & (d.quantity>0) & ~cancelled].copy()
    credits=d.loc[valid & (d.quantity<0)].copy()
    purchases['revenue']=purchases.quantity*purchases.unit_price
    credits['credit_amount']=-credits.quantity*credits.unit_price
    audit.update(purchase_lines=len(purchases),credit_lines=len(credits),
                 excluded_other_rows=len(d)-len(purchases)-len(credits),
                 anonymous_purchase_lines=int(purchases.customer_id.isna().sum()),
                 gross_sales_gbp=float(purchases.revenue.sum()), credits_gbp=float(credits.credit_amount.sum()),
                 min_timestamp=str(d.order_date.min()),max_timestamp=str(d.order_date.max()))
    if purchases.groupby('order_id').customer_id.nunique().gt(1).any():
        raise ValueError('Invoice maps to multiple known customers')
    known=purchases.dropna(subset=['customer_id'])
    orders=known.groupby(['customer_id','order_id'],as_index=False).agg(order_date=('order_date','min'),revenue=('revenue','sum'),country=('country','first'))
    return purchases,credits,orders,audit
