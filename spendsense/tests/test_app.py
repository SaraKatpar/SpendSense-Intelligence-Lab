"""Exercise navigation and a real form submission, with isolated local storage."""
import os
import sys
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import storage
from streamlit.testing.v1 import AppTest


def navigate(app,page):
    groups={'My wallet':['Allowance runway','Overview','History','Settings'],'Add spending':['Cart & online orders','Receipt studio','Add transaction'],'Plan ahead':['Survival forecast','Can I say yes?','The weekend pass','Forecast & budgets','Grocery reality check'],'Insights':['AI chat','Spending coach','Unusual activity','Spending persona','Weekly mystery','Model lab']}
    group=next(k for k,v in groups.items() if page in v)
    app.sidebar.radio[1].set_value(group).run()
    next(w for w in app.selectbox if w.label=='In this section').set_value(page).run()

def make_app():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=90)
    app.session_state['enable_checkin']=False
    return app.run()

class AppTests(unittest.TestCase):
    def test_pages_and_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            previous=storage.DB
            storage.DB=Path(directory)/'app.db'
            try:
                app=make_app()
                self.assertFalse(app.exception)
                pages=['Settings','Survival forecast','AI chat','Cart & online orders','Spending coach','Allowance runway','Can I say yes?','The weekend pass','Grocery reality check','Overview','Add transaction','Receipt studio','Forecast & budgets','Unusual activity','Spending persona','Weekly mystery','History','Model lab']
                self.assertEqual(app.sidebar.radio[0].options,['My finances','Household sample'])
                for workspace in ['My finances','Household sample']:
                    app.sidebar.radio[0].set_value(workspace).run()
                    for page in pages:
                        navigate(app,page)
                        self.assertFalse(app.exception, f'{workspace}/{page}: {list(app.exception)}')
                app.sidebar.radio[0].set_value('My finances').run()
                navigate(app,'Add transaction')
                next(w for w in app.text_input if w.label=='Description').input('Test lunch')
                next(w for w in app.number_input if w.label=='Amount (PKR)').set_value(350)
                next(w for w in app.selectbox if w.label=='Confirm category').set_value('Food')
                next(w for w in app.button if w.label=='Save transaction').click().run()
                self.assertFalse(app.exception)
                self.assertEqual(len(storage.read('My finances')),1)
                self.assertEqual(storage.read('My finances').iloc[0].amount,350)
            finally:storage.DB=previous

    def test_purchase_slider_themes_and_cash_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            previous=storage.DB;storage.DB=Path(directory)/'delight.db'
            try:
                storage.save_wallet('My finances',5000,date.fromisoformat(storage.cash_day())+timedelta(days=14),500,220,40)
                app=make_app()
                before=storage.wallet('My finances')['cash']
                navigate(app,'Can I say yes?')
                next(w for w in app.slider if w.label.startswith('Alternate timeline')).set_value(100.0).run()
                self.assertFalse(app.exception)
                self.assertEqual(next(w for w in app.number_input if w.label.startswith('What will')).value,100)
                markup=' '.join(w.value for w in app.markdown)
                self.assertIn('This fits if',markup)
                next(w for w in app.number_input if w.label.startswith('What will')).set_value(10000.0).run()
                self.assertEqual(next(w for w in app.slider if w.label.startswith('Alternate timeline')).value,10000)
                self.assertIn('Even using the full reserve',' '.join(w.value for w in app.markdown))
                self.assertEqual(storage.wallet('My finances')['cash'],before)
            finally:storage.DB=previous

    def test_receipt_review_and_save(self):
        from receipt_ocr import scan
        sample=Path(__file__).resolve().parents[1]/'data/demo_receipt.png'
        if not sample.exists():self.skipTest('Generate the fictional demo receipt first.')
        details=scan(sample.read_bytes())
        self.assertEqual(details['amount'],350)
        self.assertEqual(details['currency'],'PKR')
        with tempfile.TemporaryDirectory() as directory:
            previous=storage.DB;storage.DB=Path(directory)/'receipt.db'
            try:
                storage.save_wallet('My finances',5000,date.fromisoformat(storage.cash_day())+timedelta(days=14),500,220,40)
                app=make_app()
                before=len(storage.read('My finances'))
                cash_before=storage.wallet('My finances')['cash']
                navigate(app,'Receipt studio')
                app.session_state['receipt_details']=details
                app.run()
                next(w for w in app.text_input if w.label=='Description').input('Reviewed cafe receipt')
                next(w for w in app.button if w.label=='Save transaction').click().run()
                self.assertFalse(app.exception)
                result=storage.read('My finances')
                self.assertEqual(len(result),before+1)
                self.assertEqual(result[result.description.eq('Reviewed cafe receipt')].iloc[0].source,'receipt')
                self.assertEqual(storage.wallet('My finances')['cash'],cash_before-350)
            finally:storage.DB=previous

if __name__=='__main__':unittest.main()
