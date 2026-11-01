"""
Generates the evidence summary plot (Measured_Evidence.png) using test metrics and exports.
Run with: python -m src.report
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/processed'


def main():
    metrics_path = ROOT / 'artifacts/metrics.json'
    if not metrics_path.exists():
        print("Metrics file not found. Run 'python -m src.pipeline' first.")
        return

    test_metrics = json.loads(metrics_path.read_text())['test']
    test_preds = pd.read_csv(DATA / 'test_predictions.csv')
    precision, recall, _ = precision_recall_curve(test_preds.target, test_preds.probability)

    sales = pd.read_csv(DATA / 'daily_sales.csv').groupby('month').gross_sales.sum() / 1e6
    cohort = pd.read_csv(DATA / 'cohort_retention.csv').pivot(index='cohort', columns='month_index', values='retention_rate')
    cal = pd.read_csv(DATA / 'calibration.csv')

    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.labelcolor': '#334155',
        'text.color': '#152D42',
        'font.size': 10,
    })

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.patch.set_facecolor('#F7FAFC')

    fig.suptitle('RETENTION LENS  |  Project Evaluation & Summary', x=0.06, ha='left', fontsize=22, fontweight='bold', y=0.97)
    fig.text(
        0.06, 0.915,
        f"UCI Online Retail II  •  Test AP: {test_metrics['average_precision']:.3f}  •  Base Rate: {test_metrics['prevalence']:.1%}  •  Top-Decile Lift: {test_metrics['lift_at_top_10pct']:.2f}×",
        fontsize=12,
    )

    # 1. Gross sales trend
    ax = axes[0, 0]
    ax.plot(sales.index, sales.values, color='#0E938B', linewidth=2.5)
    ax.set_title('Gross invoiced sales (GBP millions)', loc='left', pad=15)
    ax.set_xticks(range(0, len(sales), 4))
    ax.set_xticklabels(sales.index[::4], rotation=25)
    ax.set_ylabel('GBP million')
    ax.grid(axis='y', alpha=0.15)

    # 2. Precision-recall curve
    ax = axes[0, 1]
    ax.plot(recall, precision, color='#1D4ED8', linewidth=2, label='Model (Gradient Boosting)')
    ax.axhline(test_metrics['prevalence'], linestyle='--', color='#64748B', label='Baseline (Base rate)')
    ax.set(xlabel='Recall', ylabel='Precision', xlim=(0, 1), ylim=(0, 1))
    ax.set_title('Held-out precision–recall curve', loc='left', pad=15)
    ax.legend(frameon=False)

    # 3. Cohort retention heatmap
    ax = axes[1, 0]
    img = ax.imshow(cohort.to_numpy(), vmin=0, vmax=1, cmap='YlGnBu', aspect='auto')
    ax.set_title('Cohort retention by purchase age (months)', loc='left', pad=15)
    ax.set_xlabel('Months since first purchase')
    ax.set_yticks(range(0, len(cohort), 4))
    ax.set_yticklabels(cohort.index[::4])
    fig.colorbar(img, ax=ax, fraction=0.03, pad=0.02)

    # 4. Calibration curve
    ax = axes[1, 1]
    ax.plot([0, 1], [0, 1], '--', color='#94A3B8', label='Perfect calibration')
    ax.plot(cal.mean_probability, cal.observed_rate, 'o-', color='#0E938B', label='Model predictions')
    ax.set(xlabel='Mean predicted probability', ylabel='Actual repeat purchase rate', xlim=(0, 1), ylim=(0, 1))
    ax.set_title('Probability reliability & calibration', loc='left', pad=15)
    ax.legend(frameon=False)

    fig.text(0.06, 0.025, 'Retention Lens  |  Evaluated on 21,489 held-out customer snapshots (Aug–Nov 2011)', fontsize=10, color='#475569')
    fig.subplots_adjust(top=0.85, bottom=0.11, left=0.07, right=0.96, hspace=0.48, wspace=0.3)

    output_path = ROOT / 'docs/Measured_Evidence.png'
    fig.savefig(output_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'Evidence figure saved to {output_path}')


if __name__ == '__main__':
    main()
