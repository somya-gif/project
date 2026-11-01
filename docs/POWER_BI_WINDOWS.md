# Power BI setup (Windows)

## Setup

1. Run the Python pipeline first (see README)
2. Run `python powerbi\build_project.py` — this sets the `DataFolder` parameter to your local path
3. Open `powerbi\RetentionLens.pbip` in Power BI Desktop
4. If prompted, enable the PBIP/Projects preview feature and restart
5. In **Transform data → Manage Parameters**, verify `DataFolder` points to your `data/processed` folder
6. Click **Refresh** — all eight tables should load from the CSVs

## Data model

| One side | Many side | Key |
|---|---|---|
| Calendar | Sales | date |
| Calendar | DailySales | date |
| Customers | Sales | customer_id |
| Customers | Predictions | customer_id |

Retention and Cohort tables are standalone aggregates with their own time axes.

## Verify the pages

1. **Sales** — Gross ≈ £20,476,260, Credits ≈ £1,462,424, Net ≈ £19,013,836, Orders 40,077
2. **Retention** — Previous-month retention and returning-customer share should show different values
3. **Cohorts** — Month 0 = 100%, future cells blank, observed zeros = zero
4. **Predictions** — 5,877 customers, snapshot date 2011-12-09
5. **Evidence** — Four monthly test rows matching `model_performance.csv`

## Export PBIX

After verification: **File → Save As → Power BI file (.pbix)**. Close and reopen the `.pbix` to confirm everything loads correctly.
