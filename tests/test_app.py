"""
Functional tests for the Streamlit dashboard workflows.
"""

import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class AppFlows(unittest.TestCase):

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
