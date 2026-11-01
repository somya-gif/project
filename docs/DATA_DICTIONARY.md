# Data Dictionary 📖

This guide explains what each file, number, and feature in the project means in plain English.

---

## 1. Where the Data Comes From

We use the public **UCI Online Retail II** dataset. It contains **1,067,371 rows** of real store sales from December 2009 to December 2011.

- **Important:** Each row is **one item in an invoice**, not one full order. For example, if a customer bought 5 different gift items in one visit, that order takes up 5 rows.
- **Cleaning steps:**
  - Removed 34,335 exact duplicate rows.
  - Separated cancelled orders and returns (invoices starting with `C`) from real purchases.
  - Handled rows with missing customer IDs (they count towards total store sales, but cannot be used for customer predictions).

---

## 2. Generated Files and Tables

| File Name | What is in it? | Key Column |
|---|---|---|
| `sales_orders.csv` | Every real order with total amount, date, customer ID, and country. | `order_id` |
| `customers.csv` | List of all known customers with their first purchase date and country. | `customer_id` |
| `daily_sales.csv` | Daily summary of gross sales, returns, net sales, and order counts. | `date` |
| `monthly_retention.csv` | Month-by-month summary of new vs. returning customers. | `month` |
| `cohort_retention.csv` | Tracks groups of customers by the month they first bought to see how many return over time. | `cohort` + `month` |
| `customer_predictions.csv` | Each customer's predicted chance of buying again in the next 30 days. | `customer_id` |
| `model_performance.csv` | How well the model performed month by month on test data. | `snapshot_date` |

---

## 3. Important Business Metrics Explained

- **Gross Sales:** The total money received from all purchases before returns or discounts.
- **Credits (Returns):** The money refunded for returned or cancelled items.
- **Net Sales:** Gross sales minus returns (`Net Sales = Gross Sales - Credits`).
- **Orders:** Total count of unique completed invoices.
- **Monthly Retention:** The percentage of last month's active buyers who bought again this month.
- **Cohort Retention:** The percentage of customers from a specific starting month who returned in month 1, month 2, month 3, etc.

---

## 4. Features Used by the Machine Learning Model

To predict whether a customer will buy in the next 30 days, the model looks at **11 signals** calculated strictly before the prediction date:

| Feature Name | What does it measure? | Why does it help? |
|---|---|---|
| `recency_days` | Days since the customer's last purchase. | People who bought recently are much more likely to buy again soon. |
| `tenure_days` | Days since the customer's very first order. | Shows if they are a brand new customer or a long-time customer. |
| `orders_lifetime` | Total number of orders placed so far. | Measures how loyal/frequent the customer is. |
| `revenue_lifetime` | Total money spent so far (£). | High-spending customers often have different habits. |
| `average_order_value` | Average money spent per order (`revenue / orders`). | Measures basket size. |
| `orders_30d` | Number of orders in the past 30 days. | Captures very recent activity spikes. |
| `orders_90d` | Number of orders in the past 90 days. | Captures medium-term activity. |
| `revenue_90d` | Total money spent in the past 90 days (£). | Shows recent spending power. |
| `mean_gap_days` | Average number of days between orders (-1 if only 1 order). | Helps identify customers who buy on a steady rhythm (e.g. every 2 weeks). |
| `active_months` | Number of different months the customer bought in. | Distinguishes steady repeat buyers from one-time bulk buyers. |
| `is_uk` | 1 if customer lives in the UK, 0 otherwise. | Local customers may order more frequently than international ones. |

---

## 5. What is the Target?

- **Target = 1:** The customer placed at least one real order within the next 30 days.
- **Target = 0:** The customer did not place any order in the next 30 days.
