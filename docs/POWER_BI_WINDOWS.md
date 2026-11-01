# Power BI Windows acceptance and required PBIX export

**Current state:** editable PBIP/PBIR source, not a completed PBIX. JSON schema validation does not prove that visuals render correctly or that DAX and Power Query execute in Desktop. This gate requires your Windows Power BI Desktop installation. Do not rename a ZIP or PBIP to `.pbix`.

## Open and refresh

1. Extract to a short path such as `C:\Projects\repeat_purchase`.
2. Run Python setup from README, then `.\.venv\Scripts\python.exe powerbi\build_project.py`. This sets the `DataFolder` parameter to your machine's actual path. It regenerates definitions; back up any report edits first.
3. Open `powerbi\RetentionLens.pbip` in the standard Power BI Desktop application (not Report Server Desktop).
4. If Power BI projects are behind a feature option in your installed version, enable the relevant Project/PBIP option and restart Desktop. Do not change unrelated security options.
5. In **Transform data → Manage Parameters**, verify `DataFolder` points to this project's `data/processed` folder. If it shows `/workspace/...`, replace it with your Windows folder or rerun step 2 before reopening.
6. Refresh. Check all eight tables load. No Python runtime is needed inside Power BI: it reads CSV exports.
7. Optionally import `RetentionLens_Theme.json` using **View → Themes → Browse for themes**.

## Data model

| One side | Many side | Key | Direction |
|---|---|---|---|
| Calendar | Sales | date | Single |
| Calendar | DailySales | date | Single |
| Customers | Sales | customer_id | Single |
| Customers | Predictions | customer_id | Single |

Calendar dates are at midnight. Customers includes one explicit `UNKNOWN` member for anonymous invoices. Retention, Cohorts and Performance are intentionally disconnected aggregate tables with their own time axes. Sales date filters must not imply a change to the fixed prediction snapshot. A customer-country filter must not be used to filter the aggregate DailySales table, which has no country grain.

## Check every page

1. **Sales:** With no filters, Gross Sales ≈ **£20,476,260.45**, Credits ≈ **£1,462,424.18**, Net Invoiced Sales ≈ **£19,013,836.27**, Orders **40,077**. Decimal rounding is display-only. Confirm monthly slicer changes all sales KPIs and trend. Final source day is incomplete. No profit metric exists because costs are unknown.
2. **Retention:** Previous-month retention and returning-customer share are different. First month retention should be blank. December 2011 should not appear because it is incomplete.
3. **Cohorts:** Month zero should be 100%; future/unobserved cells blank; observed inactive cells zero. Check month index sorts numerically. Row totals are intentionally blank to avoid summing retention percentages across ages.
4. **Predictions:** Full snapshot count **5,877**. Check customer ID, probability, threshold decision, recency and spend. Likelihood slicer must change the list and counts. Snapshot label is 2011-12-09. Probabilities and binary labels use different cutoffs: bands are descriptive; binary decision uses 0.27.
5. **Evidence:** Four monthly test rows. Compare them against `data/processed/model_performance.csv`. Monthly AP is not the same as pooled AP; charts show per-month values.

If a visual has a field-binding error, capture the exact Desktop error and relevant page name; do not silently remove the visual. If a definition fails to open, preserve its diagnostic. Source validation alone cannot exclude engine-specific errors.

## Produce the mandatory deliverable

1. After refresh and visual checks, choose **File → Save As**.
2. Select **Power BI file (*.pbix)** and save as `RetentionLens.pbix`.
3. Close and reopen that actual `.pbix`.
4. Repeat no-filter KPI checks, test a slicer and open all five pages.
5. Record Desktop version and results below. The project is not fully accepted until this succeeds.

| Acceptance item | Status |
|---|---|
| PBIP loads in Desktop | Pending Windows test |
| CSV refresh and DAX execute | Pending Windows test |
| All 5 pages render with correct numbers | Pending Windows test |
| Slicers and relationships behave correctly | Pending Windows test |
| Actual PBIX saved and reopened | Pending Windows test |

Reference: https://learn.microsoft.com/power-bi/developer/projects/projects-overview (Microsoft documents Desktop Save As for PBIP/PBIX conversion).
