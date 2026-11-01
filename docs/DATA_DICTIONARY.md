# Data contract and metric definitions

## Source and cleaning

Source workbook has 1,067,371 lines across two sheets. It is invoice-line grain, not one row per order or customer. Identical full rows are dropped across the combined sheets: 34,335 rows. This is a documented heuristic; without a line ID, some legitimate identical purchases could be removed. Both duplicate sensitivity and source ingestion semantics should be reviewed before real deployment.

Positive purchases require a valid timestamp, finite positive unit price, positive quantity, and an invoice not beginning with C. Negative-quantity lines at a positive price are separately booked as credits. Other records are excluded and counted. Missing customer IDs remain in financial sales; they cannot support customer-specific features. Invoice IDs are checked for conflicting known customer IDs. Invalid customer identifiers are coerced to missing; integer customer IDs are stored as text downstream.

The pipeline does not invent tax, shipping adjustments, profit or categories. Positive postage/manual charge lines can remain in invoiced revenue. Credits are not linked back to original purchases; they are booked on the credit date. The target is a positive invoice, not a delivered, retained or non-returned order. Naive source timestamps have no provided timezone; calendar boundaries use source-local time as recorded.

## Table grains

| File | One row represents | Primary key / caveat |
|---|---|---|
| sales_orders.csv | Positive invoice, including unknown customer | order_id |
| known_customer_orders.csv | Positive invoice with identified customer | customer_id + order_id |
| daily_sales.csv | Source calendar day | date; no country dimension |
| customers.csv | Identified customer | customer_id; country = last observed |
| calendar.csv | Calendar day | date |
| monthly_retention.csv | Complete calendar month | month |
| cohort_retention.csv | First-observed cohort × observed calendar month | cohort + month |
| train/validation/test_snapshots.csv | Customer at a historical prediction date | customer_id + snapshot_date |
| customer_predictions.csv | Existing customer at latest historical snapshot | customer_id |
| test_predictions.csv | Held-out customer/date outcome and score | customer_id + snapshot_date |
| calibration.csv | Probability interval in held-out test | bin |
| feature_importance.csv | Permuted feature | feature |

## Financial and customer KPIs

- Gross invoiced sales = sum of positive quantity × unit price on valid purchase lines, in GBP.
- Credits = absolute value of negative quantity × positive unit price on valid credit lines.
- Net invoiced sales = gross minus credits; not gross profit, recognized accounting revenue or cash collected.
- Orders = distinct positive invoices, including anonymous invoices.
- Active known customers = distinct nonmissing customer IDs buying in selected period.
- Repeat buyer share = fraction of active known customers with at least two invoices **inside the selected period**.
- Repeat order revenue = revenue from a known customer's second or later observed invoice over the full history; not equivalent to repeat buyer share.
- New observed customers = first observed invoice occurs in this calendar month; true acquisition could predate the dataset.
- Returning-customer share = current-month active customers whose first observed invoice predates this month / current-month active customers.
- Monthly retention = customers buying in both previous and current month / previous-month active customers. Blank when denominator is unavailable.
- Cohort retention at age k = cohort customers buying in month k / cohort size. Re-entry allowed. Only complete observed months are exported; no future months are filled with zero.

## Model features (all strictly before snapshot)

| Feature | Definition |
|---|---|
| recency_days | Days from latest historical invoice to cutoff, including fraction of day |
| tenure_days | Days since first observed invoice |
| orders_lifetime | Number of positive observed invoices |
| revenue_lifetime | Sum of positive invoiced spend |
| average_order_value | Mean historical positive invoice value |
| orders_30d / orders_90d | Invoices in [cutoff − N days, cutoff) |
| revenue_90d | Positive invoiced spend during preceding 90 days |
| mean_gap_days | (Last − first purchase time) / (orders − 1); −1 for a single order |
| active_months | Count of distinct historical calendar months with a purchase |
| is_uk | Latest pre-cutoff invoice country equals United Kingdom |

Customer ID is never a model feature. `country`, `snapshot_date` and labels are not included in the feature matrix. Known IDs include customers who bought only once; “existing” does not mean “already repeat buyer”.

Target = 1 if a known customer has any positive invoice in `[cutoff, cutoff + 30 days)`, otherwise 0. Only customers with a purchase strictly before cutoff enter that snapshot. Outcome windows must be completely observed. The last source date is partial, so its midnight is used as the exclusive reliable outcome boundary.

Floating-point CSV readers used for inference must use `float_precision='round_trip'`; tree threshold decisions can change with tiny parser rounding differences. The parity test checks all exported customer scores against the model.
