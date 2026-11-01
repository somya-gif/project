# Data dictionary

## Source

UCI Online Retail II — 1,067,371 invoice lines across two Excel sheets. Each row is a product line within an invoice, not one row per order.

Cleaning steps: drop exact duplicate rows (34,335), parse dates/numerics, separate purchases from credits (invoice prefix `C`), exclude invalid lines. Missing customer IDs stay in financial totals but are excluded from customer-level features.

## Table grains

| File | Row = | Key |
|---|---|---|
| `sales_orders.csv` | Positive invoice (incl. anonymous) | order_id |
| `known_customer_orders.csv` | Positive invoice with known customer | customer_id + order_id |
| `daily_sales.csv` | Calendar day | date |
| `customers.csv` | Known customer | customer_id |
| `calendar.csv` | Calendar day | date |
| `monthly_retention.csv` | Complete calendar month | month |
| `cohort_retention.csv` | Cohort × month | cohort + month |
| `train/validation/test_snapshots.csv` | Customer × snapshot date | customer_id + snapshot_date |
| `customer_predictions.csv` | Customer at latest snapshot | customer_id |
| `calibration.csv` | Probability bin (test set) | bin |
| `feature_importance.csv` | Feature | feature |

## KPI definitions

- **Gross invoiced sales** = Σ(quantity × unit_price) on valid purchase lines, GBP
- **Credits** = absolute value of negative-quantity lines
- **Net invoiced sales** = gross − credits
- **Orders** = distinct positive invoices
- **Monthly retention** = customers buying in both previous and current month / previous-month customers
- **Cohort retention** = cohort customers buying in month k / cohort size (re-entry allowed)

## Model features

All computed strictly before the snapshot cutoff.

| Feature | Definition |
|---|---|
| recency_days | Days since last purchase |
| tenure_days | Days since first observed purchase |
| orders_lifetime | Total positive invoices |
| revenue_lifetime | Total invoiced spend |
| average_order_value | Mean invoice value |
| orders_30d / orders_90d | Invoices in preceding 30/90 days |
| revenue_90d | Spend in preceding 90 days |
| mean_gap_days | Average days between orders (−1 if single order) |
| active_months | Distinct months with a purchase |
| is_uk | 1 if latest country = United Kingdom |

**Target:** 1 if customer has any purchase in `[cutoff, cutoff + 30 days)`, else 0.
