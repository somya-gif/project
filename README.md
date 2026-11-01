# Retention Lens 🔁

**Can we predict which customers will come back and buy again?**

That's the question I built this project around. Using transaction data from a UK online retailer (~1M rows over 2 years), I built an end-to-end machine learning pipeline that predicts whether an existing customer will make a purchase in the next 30 days.

![Evaluation Summary](docs/Measured_Evidence.png)

## What it does

- 📊 **Cleans messy retail transactions** — drops duplicates, separates returns/credits from purchases, and handles missing customer IDs
- 🧠 **Engineers point-in-time RFM features** — calculates customer recency, frequency, monetary value, tenure, and order spacing without lookahead leakage
- 🎯 **Trains & evaluates ML models** — compares a baseline, logistic regression, and histogram gradient boosting on held-out temporal test splits
- 💻 **Interactive Streamlit dashboard** — explore sales trends, look up customer repeat probabilities, analyze cohorts, and filter campaign audiences

## Key Results (Held-Out Test Set: Aug–Nov 2011)

| Metric | Value | Interpretation |
|---|---:|---|
| **Base Rate** | 20.81% | ~21% of customer snapshots had a repeat purchase |
| **Average Precision** | 0.557 | Significantly outperforms the 0.208 baseline |
| **ROC AUC** | 0.791 | Strong ranking ability across test customers |
| **Precision @ 0.27** | 53.0% | 53% of predicted buyers actually bought |
| **Recall @ 0.27** | 50.4% | Captures ~half of all repeat buyers |
| **Top-Decile Lift** | 3.14× | The top 10% scored customers buy at >3× the average rate |

The decision threshold (0.27) was selected on validation data to maximize F1 score.

## Engineering Highlight: Avoiding Data Leakage

To prevent the model from learning from future data:
1. **Strict Temporal Splits:** Training (June 2010 – Feb 2011), Validation (April – June 2011), and Test (Aug – Nov 2011) have buffer gaps so 30-day outcome windows never overlap.
2. **Point-in-Time Features:** All customer aggregations (spend, order count, recency) strictly filter `order_date < cutoff`.
3. **Automated Leakage Test:** `tests/test_features.py` programmatically modifies future data and verifies that historical features remain 100% unchanged.

## Quick Start (Windows)

Requires Python 3.12 (64-bit). You can double-click `START_WINDOWS.bat`, or run via terminal:

```powershell
# 1. Create and activate virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the pipeline (downloads data, cleans, trains models, scores customers)
python -m src.pipeline

# 4. Launch the dashboard
streamlit run app.py
```

The pipeline automatically downloads the public UCI dataset (~43.5 MB) on its first run. No API keys needed.

## Running Tests

```powershell
python -m unittest discover -s tests -v
```

All 6 feature leakage unit tests and integration tests run in under a second.

## Deployment

The app is built with Streamlit and can be deployed directly to [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud):
1. Push your repo to GitHub.
2. Connect your repo in Streamlit Community Cloud.
3. Set `app.py` as the entrypoint with Python 3.12.

## Project Structure

```
├── app.py                # 5-page Streamlit web dashboard
├── requirements.txt      # Python dependencies
├── README.md             # Project overview
├── START_WINDOWS.bat     # One-click Windows startup
├── .gitignore
├── LICENSE
├── src/
│   ├── features.py       # Data cleaning & RFM point-in-time features
│   ├── pipeline.py       # End-to-end pipeline (download, train, evaluate, score)
│   └── report.py         # Script that generates docs/Measured_Evidence.png
├── tests/
│   ├── test_features.py  # Unit tests for feature isolation & leakage prevention
│   ├── test_artifacts.py # Integration & data reconciliation tests
│   └── test_app.py       # UI flow tests
├── artifacts/
│   ├── model.joblib      # Trained Gradient Boosting model bundle
│   ├── metrics.json      # Full evaluation metrics and time splits
│   └── data_quality.json # Ingestion audit counts
└── docs/
    ├── DATA_DICTIONARY.md # Schema and column definitions
    ├── MODEL_CARD.md      # Model assumptions and tradeoffs
    └── Measured_Evidence.png
```

## Dataset Attribution

Chen, D. (2012). **Online Retail II** [Dataset]. UCI Machine Learning Repository.  
https://doi.org/10.24432/C5CG6D (Licensed under CC BY 4.0).
