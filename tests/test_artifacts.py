import json,unittest
from pathlib import Path
import joblib,numpy as np,pandas as pd
from src.features import FEATURES

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/processed'
class ArtifactIntegrity(unittest.TestCase):
    def test_export_scores_match_model(self):
        m=joblib.load(ROOT/'artifacts/model.joblib');d=pd.read_csv(DATA/'customer_predictions.csv',float_precision='round_trip')
        np.testing.assert_allclose(m['model'].predict_proba(d[FEATURES])[:,1],d.probability,atol=1e-10)
        self.assertTrue(d.customer_id.is_unique)
        self.assertTrue(d.probability.between(0,1).all())
    def test_sales_reconcile(self):
        d=pd.read_csv(DATA/'daily_sales.csv');o=pd.read_csv(DATA/'sales_orders.csv')
        q=json.loads((ROOT/'artifacts/data_quality.json').read_text())
        self.assertAlmostEqual(d.gross_sales.sum(),q['gross_sales_gbp'],places=5)
        self.assertAlmostEqual(o.revenue.sum(),q['gross_sales_gbp'],places=5)
        self.assertAlmostEqual(d.credits.sum(),q['credits_gbp'],places=5)
        self.assertEqual(int(d.orders.sum()),len(o))
    def test_cohorts_mature_and_valid(self):
        d=pd.read_csv(DATA/'cohort_retention.csv')
        self.assertTrue(d.retention_rate.between(0,1).all())
        self.assertTrue((d.loc[d.month_index==0,'retention_rate']==1).all())
        self.assertLess(d.month.max(),'2011-12')
    def test_splits_purged_and_unique(self):
        s=[pd.read_csv(DATA/f'{x}_snapshots.csv',parse_dates=['snapshot_date']) for x in ['train','validation','test']]
        for a,b in zip(s,s[1:]):self.assertLess(a.snapshot_date.max()+pd.Timedelta(days=30),b.snapshot_date.min())
        for a in s:self.assertFalse(a.duplicated(['customer_id','snapshot_date']).any())

if __name__=='__main__':unittest.main()
