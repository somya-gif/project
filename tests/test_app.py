"""
Functional tests for the Streamlit dashboard workflows.
"""

import unittest
from pathlib import Path

try:
    from streamlit.testing.v1 import AppTest
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

ROOT = Path(__file__).resolve().parents[1]


class AppFlows(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not HAS_STREAMLIT:
            raise unittest.SkipTest("Streamlit is not installed in the current Python environment.")
        data_pred = ROOT / 'data/processed/customer_predictions.csv'
        if not data_pred.exists():
            raise unittest.SkipTest("Run 'python -m src.pipeline' first to generate data for app tests.")

    def test_all_pages_and_customer_selection(self):
        """Verifies all five app tabs and customer dropdown work without exceptions."""
        app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=40)
        self.assertFalse(app.exception)

        pages = ['Customer prediction', 'Retention cohorts', 'Campaign shortlist', 'Model evidence']
        for page in pages:
            app.sidebar.radio[0].set_value(page).run(timeout=40)
            self.assertFalse(app.exception, msg=f'Failed on page {page}')
            if page == 'Customer prediction':
                app.selectbox[0].select_index(10).run(timeout=40)
                self.assertFalse(app.exception)

    def test_empty_audience(self):
        """Verifies filtering down to an empty audience displays 0 rows without error."""
        app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=40)
        app.sidebar.radio[0].set_value('Campaign shortlist').run()
        app.multiselect[0].set_value([]).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '0')


if __name__ == '__main__':
    unittest.main()
