# Retention Lens 🔁

**Can we predict which customers will come back and buy again?**

That's the question I built this project around. Using real transaction data from a UK online retailer (~1M rows over 2 years), I built an end-to-end ML pipeline that predicts whether a customer will make a purchase in the next 30 days.

![Measured historical evaluation](docs/Measured_Evidence.png)

## What it does

- 📊 **Cleans messy retail data** — handles duplicates, missing IDs, returns/credits, and invalid rows
- 🧠 **Trains a prediction model** — compared 3 approaches, gradient boosting came out on top
- 🎯 **Scores every customer** — each gets a repeat-purchase probability (the top 10% of scored customers buy at 3.14× the average rate)
- 💻 **Interactive Streamlit app** — explore sales trends, look up individual customers, build campaign audiences
- 📈 **Power BI report** — 5-page dashboard covering sales, retention, cohorts, predictions, and model performance

## The interesting bits

The model achieves **0.557 average precision** against a 20.8% base rate — meaning it's significantly better than random at finding who'll buy next. The top-scored 10% of customers contain 65% actual repeat buyers.

I was careful about **data leakage** — the model only ever sees past data when making predictions. Train, validation, and test sets are separated by time with gaps between them, just like you'd need in production. There's even a [test](tests/test_features.py) that proves changing future data doesn't affect historical features.

One fun bug I caught: default CSV parsing rounds floats at the 8th decimal, which was enough to flip 2 out of 5,877 predictions at a tree split boundary. Fixed it with `float_precision='round_trip'`.

## Quick start

Needs Python 3.12. On Windows, just double-click `START_WINDOWS.bat`, or:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.pipeline     # downloads data & trains (~5 min)
.\.venv\Scripts\python.exe -m streamlit run app.py
```

No API keys needed — the pipeline downloads the [public UCI dataset](https://doi.org/10.24432/C5CG6D) automatically.

## Test results (held-out, Aug–Nov 2011)

| What | Value |
|---|---:|
| Customers scored | 21,489 snapshots |
| Actually bought again | 20.81% |
| Average precision | 0.557 |
| ROC AUC | 0.791 |
| Precision @ threshold | 53% |
| Recall @ threshold | 50% |
| Top-decile lift | 3.14× |

## Project layout

```
src/features.py      Feature engineering + data cleaning
src/pipeline.py      Full ML pipeline (download → train → evaluate → export)
app.py               Streamlit app (5 pages)
powerbi/             Power BI report (open RetentionLens.pbip)
tests/               Unit + integration tests (leakage, parity, reconciliation)
artifacts/           Trained model, metrics, data provenance
docs/                Model card, data dictionary, setup guides
```

## How I'd take this further

- Add seasonal features (holiday spending patterns differ a lot)
- Calibrate the probabilities properly on a dedicated time block
- Run an A/B test to measure if targeting high-probability customers actually increases revenue (prediction ≠ causation)
- Hook it up to a live data feed with monitoring for feature drift

## Data

[UCI Online Retail II](https://doi.org/10.24432/C5CG6D) by Daqing Chen · CC BY 4.0
