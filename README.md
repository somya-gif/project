# Retention Lens

E-commerce analytics and 30-day repeat purchase prediction.

![Measured historical evaluation](docs/Measured_Evidence.png)

Built on the UCI Online Retail II dataset (~1M transaction lines, Dec 2009–Dec 2011). The pipeline cleans raw transactions, engineers point-in-time customer features, trains a gradient boosting model, and serves predictions through both a Streamlit app and a Power BI report.

## Quick start (Windows)

Requires Python 3.12 (64-bit). Double-click `START_WINDOWS.bat`, or run manually:

```powershell
cd C:\Projects\repeat_purchase
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.pipeline
.\.venv\Scripts\python.exe powerbi\build_project.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The pipeline downloads the public UCI source (~43.5 MB) and generates all local data. No API keys needed.

## Retrain & test

```powershell
$env:OMP_NUM_THREADS="2"
$env:OPENBLAS_NUM_THREADS="2"
.\.venv\Scripts\python.exe -m src.pipeline
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Held-out test results

| Metric | Value |
|---|---:|
| Test snapshots | 21,489 |
| Base rate | 20.81% |
| Average precision | 0.5569 |
| ROC AUC | 0.7906 |
| Precision @ 0.27 | 52.98% |
| Recall @ 0.27 | 50.37% |
| F1 | 0.5164 |
| Top-decile lift | 3.14× |

Threshold 0.27 was chosen to maximize validation F1. Evaluation uses August–November 2011 snapshots with strict temporal separation from training.

## Streamlit app

- **Sales overview** — gross/net sales, credits, orders, trend
- **Customer prediction** — select a customer, see repeat-purchase probability and order history
- **Retention cohorts** — monthly cohort matrix, returning-customer trends
- **Campaign shortlist** — filter by likelihood/spend, upload customer IDs, download scores
- **Model evidence** — test metrics, monthly performance, calibration, feature importance

## Power BI

Run `python powerbi/build_project.py`, then open `powerbi/RetentionLens.pbip` in Power BI Desktop and refresh. Five report pages with DAX measures included. See [Power BI setup guide](docs/POWER_BI_WINDOWS.md).

## Project structure

| Path | Purpose |
|---|---|
| `src/features.py` | Data cleaning and point-in-time feature engineering |
| `src/pipeline.py` | Download, train, evaluate, export |
| `app.py` | Streamlit app |
| `data/processed/` | Generated CSVs (git-ignored) |
| `artifacts/` | Trained model, metrics, provenance |
| `powerbi/` | Report source, semantic model, DAX, theme |
| `tests/` | Unit and integration tests |
| `docs/` | Model card, data dictionary, setup guides |

## Data source

Chen, D. (2012). **Online Retail II** [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C5CG6D — License: CC BY 4.0.
