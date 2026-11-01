"""
Unit tests for point-in-time feature extraction and data cleaning.
"""

import unittest
import numpy as np
import pandas as pd
from src.features import FEATURES, quality_and_clean, snapshot


class PointInTimeTests(unittest.TestCase):

    def setUp(self):
        self.orders = pd.DataFrame({
            'customer_id': ['1', '1', '2', '3', '1'],
            'order_id': ['a', 'b', 'c', 'd', 'e'],
            'order_date': pd.to_datetime(['2020-01-01', '2020-02-01', '2020-02-01', '2020-01-10', '2020-03-02']),
            'revenue': [10.0, 20.0, 30.0, 40.0, 50.0],
            'country': ['UK'] * 5,
        })

    def test_cutoff_excludes_current_and_future_from_features(self):
        # Customer 1 has order on Feb 1; at cutoff Feb 1, only Jan 1 order should be counted in history
        snaps = snapshot(self.orders, '2020-02-01', with_label=True, observation_end='2020-04-01').set_index('customer_id')
        self.assertEqual(set(snaps.index), {'1', '3'})
        self.assertEqual(snaps.loc['1', 'orders_lifetime'], 1)
        self.assertEqual(snaps.loc['1', 'revenue_lifetime'], 10.0)
        self.assertEqual(snaps.loc['1', 'target'], 1)
        self.assertEqual(snaps.loc['3', 'target'], 0)

    def test_future_changes_do_not_change_features(self):
        # Changing future orders should have zero impact on past features (leakage test)
        original = snapshot(self.orders, '2020-02-01')
        altered = self.orders.copy()
        altered.loc[altered.order_date >= '2020-02-01', 'revenue'] = 999999.0
        pd.testing.assert_frame_equal(original, snapshot(altered, '2020-02-01'))

    def test_end_boundary_is_exclusive(self):
        # Feb 1 + 30 days = Mar 2 (in 2020 leap year); an order exactly on Mar 2 should not count
        orders_without_b = self.orders[self.orders.order_id != 'b']
        snaps = snapshot(orders_without_b, '2020-02-01', with_label=True, observation_end='2020-04-01').set_index('customer_id')
        self.assertEqual(snaps.loc['1', 'target'], 0)

    def test_censoring_rejected(self):
        # If observation window ends before cutoff + 30 days, should raise error
        with self.assertRaises(ValueError):
            snapshot(self.orders, '2020-02-01', with_label=True, observation_end='2020-02-20')

    def test_features_finite(self):
        # All computed features must be finite numeric values
        snaps = snapshot(self.orders, '2020-02-01')
        self.assertTrue(np.isfinite(snaps[FEATURES]).all().all())

    def test_cleaning_keeps_anonymous_sales_and_separates_credit(self):
        raw_mock = pd.DataFrame({
            'Invoice': ['1', '1', 'C2', '3'],
            'StockCode': ['a'] * 4,
            'Quantity': [1, 1, -1, 2],
            'InvoiceDate': ['2020-01-01'] * 4,
            'Price': [5.0] * 4,
            'Customer ID': [1, 1, 1, None],
            'Country': ['UK'] * 4,
        })
        purchases, credits, orders, audit = quality_and_clean(raw_mock)
        self.assertEqual(audit['exact_duplicate_rows'], 1)
        self.assertEqual(purchases.revenue.sum(), 15.0)
        self.assertEqual(credits.credit_amount.sum(), 5.0)
        self.assertEqual(len(orders), 1)


if __name__ == '__main__':
    unittest.main()
