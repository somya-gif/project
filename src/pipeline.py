"""
End-to-end data and machine learning pipeline for repeat purchase prediction.
Run directly with: python -m src.pipeline
"""

import json
import sys
import urllib.request
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES, quality_and_clean, snapshot

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/processed'
ARTIFACTS = ROOT / 'artifacts'
DATA_URL = 'https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip'


def dump_json(path: Path, obj: dict):
    """Utility to write formatted JSON files."""
    path.write_text(json.dumps(obj, indent=2, default=str), encoding='utf-8')


def calculate_metrics(y_true, y_prob, threshold: float) -> dict:
    """Calculates classification evaluation metrics and top-decile lift."""
    pred = y_prob >= threshold
    top_n = max(1, int(np.ceil(len(y_true) * 0.1)))
    top_indices = np.argsort(-y_prob, kind='stable')[:top_n]
    base_rate = float(np.mean(y_true))

    return {
        'n': len(y_true),
        'positives': int(np.sum(y_true)),
        'prevalence': base_rate,
        'average_precision': float(average_precision_score(y_true, y_prob)),
        'roc_auc': float(roc_auc_score(y_true, y_prob)),
        'brier_score': float(brier_score_loss(y_true, y_prob)),
        'precision': float(precision_score(y_true, pred, zero_division=0)),
        'recall': float(recall_score(y_true, pred, zero_division=0)),
        'f1': float(f1_score(y_true, pred, zero_division=0)),
        'precision_at_top_10pct': float(np.asarray(y_true)[top_indices].mean()),
        'lift_at_top_10pct': float(np.asarray(y_true)[top_indices].mean() / base_rate),
        'confusion_matrix_tn_fp_fn_tp': confusion_matrix(y_true, pred, labels=[0, 1]).ravel().tolist(),
    }


def export_analytics_tables(purchases: pd.DataFrame, credits: pd.DataFrame, orders: pd.DataFrame, end_date: pd.Timestamp):
    """
    Exports clean analytical tables used by the Streamlit app:
    - sales_orders.csv
    - customers.csv
    - calendar.csv
    - daily_sales.csv
    - cohort_retention.csv
    - monthly_retention.csv
    """
    # 1. Sales orders (preserving anonymous transactions in totals)
    all_orders = (
        purchases.assign(customer_id=purchases.customer_id.fillna('UNKNOWN'))
        .groupby('order_id', as_index=False)
        .agg(
            customer_id=('customer_id', 'first'),
            order_date=('order_date', 'min'),
            revenue=('revenue', 'sum'),
            units=('quantity', 'sum'),
            country=('country', 'first'),
        )
    )
    all_orders = all_orders.sort_values(['order_date', 'order_id'])
    all_orders['is_repeat_order'] = (
        (all_orders.groupby('customer_id').cumcount() > 0) & (all_orders.customer_id != 'UNKNOWN')
    ).astype(int)
    all_orders['date'] = all_orders.order_date.dt.strftime('%Y-%m-%d')
    all_orders['month'] = all_orders.order_date.dt.strftime('%Y-%m')
    all_orders.to_csv(DATA / 'sales_orders.csv', index=False)

    # 2. Customers dimension
    customers = (
        orders.sort_values('order_date')
        .groupby('customer_id', as_index=False)
        .agg(
            first_observed_purchase=('order_date', 'min'),
            country=('country', 'last'),
        )
    )
    customers['cohort'] = customers.first_observed_purchase.dt.strftime('%Y-%m')
    customers.to_csv(DATA / 'customers.csv', index=False)

    # 3. Calendar dimension
    calendar_df = pd.DataFrame({
        'date': pd.date_range(purchases.order_date.min().normalize(), end_date, freq='D')
    })
    calendar_df['month'] = calendar_df.date.dt.strftime('%Y-%m')
    calendar_df['year'] = calendar_df.date.dt.year
    calendar_df['date'] = calendar_df.date.dt.strftime('%Y-%m-%d')
    calendar_df.to_csv(DATA / 'calendar.csv', index=False)

    # 4. Daily sales aggregates
    daily = (
        all_orders.groupby('date', as_index=False)
        .agg(gross_sales=('revenue', 'sum'), orders=('order_id', 'size'), units=('units', 'sum'))
    )
    credit_daily = (
        credits.assign(date=credits.order_date.dt.strftime('%Y-%m-%d'))
        .groupby('date')
        .credit_amount.sum()
    )

    daily = calendar_df[['date']].merge(daily, on='date', how='left').fillna(0)
    daily['credits'] = daily.date.map(credit_daily).fillna(0)
    daily['net_invoiced_sales'] = daily.gross_sales - daily.credits
    daily['month'] = daily.date.str[:7]
    daily.to_csv(DATA / 'daily_sales.csv', index=False)

    # 5. Cohort retention matrix (complete months only)
    complete_orders = orders[orders.order_date < end_date.to_period('M').start_time].copy()
    complete_orders['month'] = complete_orders.order_date.dt.to_period('M')
    first_purchase_month = orders.groupby('customer_id').order_date.min().dt.to_period('M')
    complete_orders['cohort'] = complete_orders.customer_id.map(first_purchase_month)

    cohort_counts = complete_orders.groupby(['cohort', 'month']).customer_id.nunique()
    cohort_sizes = first_purchase_month.value_counts()
    last_month = end_date.to_period('M') - 1

    cohort_rows = []
    for cohort in sorted(first_purchase_month.unique()):
        for month in pd.period_range(cohort, last_month, freq='M'):
            active = int(cohort_counts.get((cohort, month), 0))
            base_size = int(cohort_sizes[cohort])
            cohort_rows.append({
                'cohort': str(cohort),
                'month': str(month),
                'month_index': month.ordinal - cohort.ordinal,
                'active_customers': active,
                'cohort_size': base_size,
                'retention_rate': active / base_size,
            })
    pd.DataFrame(cohort_rows).to_csv(DATA / 'cohort_retention.csv', index=False)

    # 6. Monthly retention and returning customer mix
    monthly_rows = []
    for month, group in complete_orders.groupby('month'):
        active_set = set(group.customer_id)
        prev_set = set(complete_orders.loc[complete_orders.month == month - 1, 'customer_id'])
        returning_count = sum(first_purchase_month[cust] < month for cust in active_set)
        retained_count = len(active_set & prev_set)

        monthly_rows.append({
            'month': str(month),
            'active_customers': len(active_set),
            'new_observed_customers': len(active_set) - returning_count,
            'returning_customers': returning_count,
            'previous_month_customers': len(prev_set),
            'retained_from_previous_month': retained_count,
            'monthly_retention_rate': retained_count / len(prev_set) if prev_set else np.nan,
            'returning_customer_share': returning_count / len(active_set),
        })
    pd.DataFrame(monthly_rows).to_csv(DATA / 'monthly_retention.csv', index=False)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(exist_ok=True)
    raw_dir = ROOT / 'data/raw'
    raw_dir.mkdir(exist_ok=True)

    xlsx_path = raw_dir / 'online_retail_II.xlsx'
    archive_path = raw_dir / 'online_retail_ii.zip'

    # Download source workbook if not locally present
    if not xlsx_path.exists():
        if not archive_path.exists():
            print(f'Downloading UCI dataset from {DATA_URL}...', flush=True)
            urllib.request.urlretrieve(DATA_URL, archive_path)
        with zipfile.ZipFile(archive_path) as z:
            xlsx_path.write_bytes(z.read('online_retail_II.xlsx'))

    print('Reading and parsing transactions from Excel...', flush=True)
    source = pd.concat(pd.read_excel(xlsx_path, sheet_name=None).values(), ignore_index=True)

    print('Cleaning raw data...', flush=True)
    purchases, credits, orders, audit = quality_and_clean(source)

    # Use midnight of the last recorded day as the observation boundary
    observation_end = pd.Timestamp(audit['max_timestamp']).normalize()

    orders.to_csv(DATA / 'known_customer_orders.csv', index=False)
    dump_json(ARTIFACTS / 'data_quality.json', audit)

    print('Exporting analytics tables...', flush=True)
    export_analytics_tables(purchases, credits, orders, observation_end)

    # Define time-based train, validation, and test snapshot dates
    split_dates = {
        'train': pd.date_range('2010-06-01', '2011-02-01', freq='MS'),
        'validation': pd.date_range('2011-04-01', '2011-06-01', freq='MS'),
        'test': pd.date_range('2011-08-01', '2011-11-01', freq='MS'),
    }

    # Ensure no temporal label overlap
    assert split_dates['train'].max() + pd.Timedelta(days=30) < split_dates['validation'].min()
    assert split_dates['validation'].max() + pd.Timedelta(days=30) < split_dates['test'].min()

    print('Generating point-in-time features for all splits...', flush=True)
    splits = {
        name: pd.concat([snapshot(orders, d, with_label=True, observation_end=observation_end) for d in dates], ignore_index=True)
        for name, dates in split_dates.items()
    }
    for name, df in splits.items():
        df.to_csv(DATA / f'{name}_snapshots.csv', index=False)

    train_df, val_df, test_df = splits['train'], splits['validation'], splits['test']

    # Model candidates
    candidates = {
        'base_rate': DummyClassifier(strategy='prior'),
        'logistic': make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500, random_state=42)),
        'gradient_boosting': HistGradientBoostingClassifier(
            max_iter=160,
            max_leaf_nodes=15,
            l2_regularization=10,
            learning_rate=0.06,
            early_stopping=False,
            random_state=42,
        ),
    }

    fitted_models = {}
    validation_comparison = []

    print('Training candidate models...', flush=True)
    for name, model in candidates.items():
        print(f' - Training {name}', flush=True)
        model.fit(train_df[FEATURES], train_df.target)
        val_probs = model.predict_proba(val_df[FEATURES])[:, 1]
        fitted_models[name] = model
        validation_comparison.append({
            'model': name,
            **calculate_metrics(val_df.target, val_probs, 0.5),
        })

    # Select best model by validation average precision
    best_name = max(validation_comparison, key=lambda row: row['average_precision'])['model']
    selected_model = fitted_models[best_name]
    print(f'Selected best model: {best_name}', flush=True)

    # Determine decision threshold that maximizes validation F1
    val_probs = selected_model.predict_proba(val_df[FEATURES])[:, 1]
    candidate_thresholds = np.arange(0.05, 0.81, 0.01)
    best_threshold = float(max(
        candidate_thresholds,
        key=lambda thresh: f1_score(val_df.target, val_probs >= thresh, zero_division=0),
    ))
    print(f'Optimal decision threshold: {best_threshold:.2f}', flush=True)

    # Final evaluation on held-out test data
    test_probs = selected_model.predict_proba(test_df[FEATURES])[:, 1]
    test_metrics = calculate_metrics(test_df.target, test_probs, best_threshold)

    report = {
        'selected_model': best_name,
        'selection_metric': 'validation average precision',
        'threshold': best_threshold,
        'threshold_policy': 'Validation F1 maximum',
        'features': FEATURES,
        'splits': {k: [str(x.date()) for x in ds] for k, ds in split_dates.items()},
        'validation_candidates': validation_comparison,
        'test': test_metrics,
        'test_base_rate': calculate_metrics(
            test_df.target,
            fitted_models['base_rate'].predict_proba(test_df[FEATURES])[:, 1],
            0.5,
        ),
    }

    # Save test predictions and monthly breakout
    test_predictions = test_df[['customer_id', 'snapshot_date', 'target']].copy()
    test_predictions['probability'] = test_probs
    test_predictions.to_csv(DATA / 'test_predictions.csv', index=False)

    monthly_performance = []
    for snapshot_dt, group in test_predictions.groupby('snapshot_date'):
        monthly_performance.append({
            'snapshot_date': str(snapshot_dt.date()),
            **calculate_metrics(group.target, group.probability.to_numpy(), best_threshold),
        })
    report['test_by_month'] = monthly_performance
    pd.DataFrame(monthly_performance).drop(columns=['confusion_matrix_tn_fp_fn_tp']).to_csv(
        DATA / 'model_performance.csv', index=False
    )

    # Reliability / calibration bins
    reliability = (
        test_predictions.assign(bin=pd.cut(test_probs, np.linspace(0, 1, 11), include_lowest=True))
        .groupby('bin', observed=True)
        .agg(
            mean_probability=('probability', 'mean'),
            observed_rate=('target', 'mean'),
            count=('target', 'size'),
        )
        .reset_index()
    )
    reliability.to_csv(DATA / 'calibration.csv', index=False)

    # Permutation feature importance
    print('Calculating feature importance...', flush=True)
    importance = permutation_importance(
        selected_model,
        val_df[FEATURES],
        val_df.target,
        scoring='average_precision',
        n_repeats=3,
        random_state=42,
    )
    pd.DataFrame({
        'feature': FEATURES,
        'ap_decrease': importance.importances_mean,
        'std': importance.importances_std,
    }).sort_values('ap_decrease', ascending=False).to_csv(DATA / 'feature_importance.csv', index=False)

    # Final scoring on the latest cutoff for production demo
    print('Scoring current customer base for interactive app...', flush=True)
    latest_snapshot = snapshot(orders, observation_end)
    latest_snapshot['probability'] = selected_model.predict_proba(latest_snapshot[FEATURES])[:, 1]
    latest_snapshot['predicted_repeat'] = (latest_snapshot.probability >= best_threshold).astype(int)
    latest_snapshot['likelihood_band'] = pd.cut(
        latest_snapshot.probability,
        [-0.001, 0.20, 0.50, 1.0],
        labels=['Low', 'Medium', 'High'],
    ).astype(str)
    latest_snapshot['model_version'] = 'retail-v1'
    latest_snapshot.to_csv(DATA / 'customer_predictions.csv', index=False)

    # Save model artifact bundle
    bundle = {
        'model': selected_model,
        'features': FEATURES,
        'threshold': best_threshold,
        'snapshot_date': str(observation_end.date()),
        'model_version': 'retail-v1',
    }
    joblib.dump(bundle, ARTIFACTS / 'model.joblib', compress=3)
    dump_json(ARTIFACTS / 'metrics.json', report)

    print('Pipeline complete! Summary:')
    print(json.dumps({
        'model': best_name,
        'threshold': best_threshold,
        'test_average_precision': test_metrics['average_precision'],
        'test_base_rate': test_metrics['prevalence'],
        'top_10pct_lift': test_metrics['lift_at_top_10pct'],
    }, indent=2), flush=True)


if __name__ == '__main__':
    main()
