import unittest
import pandas as pd
from src.features import snapshot, FEATURES, quality_and_clean

class PointInTimeTests(unittest.TestCase):
    def setUp(self):
        self.orders=pd.DataFrame({'customer_id':['1','1','2','3','1'], 'order_id':['a','b','c','d','e'],
            'order_date':pd.to_datetime(['2020-01-01','2020-02-01','2020-02-01','2020-01-10','2020-03-02']),
            'revenue':[10.,20.,30.,40.,50.],'country':['UK']*5})
    def test_cutoff_excludes_current_and_future_from_features(self):
        s=snapshot(self.orders,'2020-02-01',True,'2020-04-01').set_index('customer_id')
        self.assertEqual(set(s.index),{'1','3'})
        self.assertEqual(s.loc['1','orders_lifetime'],1)
        self.assertEqual(s.loc['1','revenue_lifetime'],10)
        self.assertEqual(s.loc['1','target'],1)
        self.assertEqual(s.loc['3','target'],0)
    def test_future_changes_do_not_change_features(self):
        original=snapshot(self.orders,'2020-02-01')
        altered=self.orders.copy();altered.loc[altered.order_date>='2020-02-01','revenue']=999999
        pd.testing.assert_frame_equal(original,snapshot(altered,'2020-02-01'))
    def test_end_boundary_is_exclusive(self):
        # Feb 1 + 30 days = Mar 2 (leap year); Mar 2 does not count.
        o=self.orders[self.orders.order_id!='b']
        s=snapshot(o,'2020-02-01',True,'2020-04-01').set_index('customer_id')
        self.assertEqual(s.loc['1','target'],0)
    def test_censoring_rejected(self):
        with self.assertRaises(ValueError):snapshot(self.orders,'2020-02-01',True,'2020-02-20')
    def test_features_finite(self):
        import numpy as np
        self.assertTrue(np.isfinite(snapshot(self.orders,'2020-02-01')[FEATURES]).all().all())
    def test_cleaning_keeps_anonymous_sales_and_separates_credit(self):
        d=pd.DataFrame({'Invoice':['1','1','C2','3'],'StockCode':['a']*4,'Quantity':[1,1,-1,2],
          'InvoiceDate':['2020-01-01']*4,'Price':[5]*4,'Customer ID':[1,1,1,None],'Country':['UK']*4})
        purchases,credits,orders,audit=quality_and_clean(d)
        self.assertEqual(audit['exact_duplicate_rows'],1)
        self.assertEqual(purchases.revenue.sum(),15)
        self.assertEqual(credits.credit_amount.sum(),5)
        self.assertEqual(len(orders),1)

if __name__=='__main__':unittest.main()
