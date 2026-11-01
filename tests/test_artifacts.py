"""
Integration tests verifying generated artifacts, reconciliations, and split boundaries.
"""

import json
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from src.features import FEATURES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/processed'


class ArtifactIntegrity(unittest.TestCase):

    def test_export_scores_match_model(self):
        """Verifies exported probabilities match direct model predictions."""
        bundle = joblib.load(ROOT / 'artifacts/model.joblib')
        df = pd.read_csv(DATA / 'customer_predictions.csv', float_precision='round_trip')
        model_probs = bundle['model'].predict_proba(df[FEATURES])[:, 1]
        np.testing.assert_allclose(model_probs, df.probability, atol=1e-10)
        self.assertTrue(df.customer_id.is_unique)
        self.assertTrue(df.probability.between(0, 1).all())

    def test_sales_reconcile(self):
        """Verifies daily aggregates reconcile with order-level totals and audit logs."""
        daily = pd.read_csv(DATA / 'daily_sales.csv')
        orders = pd.read_csv(DATA / 'sales_orders.csv')
        quality = json.loads((ROOT / 'artifacts/data_quality.json').read_text())

        self.assertAlmostEqual(daily.gross_sales.sum(), quality['gross_sales_gbp'], places=5)
        self.assertAlmostEqual(orders.revenue.sum(), quality['gross_sales_gbp'], places=5)
        self.assertAlmostEqual(daily.credits.sum(), quality['credits_gbp'], places=5)
        self.assertEqual(int(daily.orders.sum()), len(orders))

    def test_cohorts_mature_and_valid(self):
        """Verifies cohort retention boundaries and completeness."""
        cohorts = pd.read_csv(DATA / 'cohort_retention.csv')
        self.assertTrue(cohorts.retention_rate.between(0, 1).all())
        self.assertTrue((cohorts.loc[cohorts.month_index == 0, 'retention_rate'] == 1).all())
        self.assertLess(cohorts.month.max(), '2011-12')

    def test_splits_purged_and_unique(self):
        """Verifies train, validation, and test splits have temporal buffers and unique snapshots."""
        splits = [
            pd.read_csv(DATA / f'{split}_snapshots.csv', parse_dates=['snapshot_date'])
            for split in ['train', 'validation', 'test']
        ]
        for current_split, next_split in zip(splits, splits[1:]):
            self.assertLess(
                current_split.snapshot_date.max() + pd.Timedelta(days=30),
                next_split.snapshot_date.min(),
            )
        for split_df in splits:
            self.assertFalse(split_df.duplicated(['customer_id', 'snapshot_date']).any())


if __name__ == '__main__':
    unittest.main()
