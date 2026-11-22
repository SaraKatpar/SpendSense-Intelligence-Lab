"""F01–F04 and replay regressions; isolated DBs, no model evaluation."""
import sys,tempfile,unittest,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import storage
from app.finance import currency_of,enforce_currency,money
from capture import parse_expenses,save_batch
from shopping import carts,order_fields
from receipt_ocr import extract_fields
from chat_actions import prepare,apply


class AccountingP0Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=storage.DB;storage.DB=Path(self.tmp.name)/'p0.db'
        self.today=date.fromisoformat(storage.cash_day())
        storage.save_wallet('My finances',100,self.today+timedelta(days=14),0,0,0)
        self.entry={'date':str(self.today),'amount':.005,'kind':'Expense','category':'Food','description':'Lunch'}
    def tearDown(self):storage.DB=self.old;self.tmp.cleanup()
    def test_f01_currency_detection_and_mixed_precedence(self):
        for token,code in [('$','USD'),('€','EUR'),('£','GBP'),('₹','INR'),('RM','MYR'),('AED','AED')]:
            text=f'Order total: {token}120.00'
            self.assertEqual(order_fields(text)['currency'],code)
            self.assertEqual(extract_fields(text)['currency'],code)
            with self.assertRaises(ValueError):enforce_currency('My finances',text=text)
        self.assertEqual(currency_of('PKR 100 and $20'),'MIXED')
        with self.assertRaises(ValueError):storage.add('My finances',self.today,120,'Expense','Shopping','Cart $120',affects_cash=True,currency='PKR')
        with self.assertRaises(ValueError):carts('My finances','foreign',120,currency='USD')
        self.assertTrue(storage.read('My finances').empty)
    def test_f02_csv_currency_checked_atomically_and_exported(self):
        rows=pd.DataFrame([dict(self.entry,currency='PKR'),dict(self.entry,currency='USD')])
        with self.assertRaises(ValueError):storage.import_csv('My finances',rows)
        self.assertTrue(storage.read('My finances').empty)
        with self.assertRaises(ValueError):storage.import_csv('My finances',pd.DataFrame([dict(self.entry,currency='INR')]))
        storage.import_csv('Household sample',pd.DataFrame([dict(self.entry,currency='INR')]))
        self.assertEqual(storage.read('Household sample').iloc[0].currency,'INR')
        self.assertEqual(storage.wallet('My finances')['cash'],100)
    def test_f03_dates_are_per_expense_for_both_relative_and_iso(self):
        yesterday=self.today-timedelta(days=1)
        rows=parse_expenses('Spent 350 on lunch yesterday and 150 on rickshaw today',self.today)
        self.assertEqual([r['date'] for r in rows],[yesterday,self.today])
        rows=parse_expenses(f'350 lunch on {yesterday}; 150 transport today',self.today)
        self.assertEqual([r['date'] for r in rows],[yesterday,self.today])
        rows=parse_expenses('yesterday spent 350 on lunch and today 150 on rickshaw',self.today)
        self.assertEqual([r['date'] for r in rows],[yesterday,self.today])
        with self.assertRaises(ValueError):parse_expenses('350 lunch today yesterday',self.today)
        with self.assertRaises(ValueError):parse_expenses('PKR 350 lunch and $150 rickshaw',self.today)
    def test_f04_round_before_ledger_cash_refund_and_reversal(self):
        self.assertEqual(money('.005',True),.01);self.assertEqual(money('2.675'),2.68)
        with self.assertRaises(ValueError):money('.004',True)
        first=storage.add('My finances',self.today,.005,'Expense','Food','Lunch',affects_cash=True)
        self.assertEqual(storage.read('My finances').iloc[0].amount,.01)
        self.assertEqual(storage.wallet('My finances')['cash'],99.99)
        refund=storage.add('My finances',self.today,.005,'Income','Other','Refund',affects_cash=True)
        self.assertEqual(storage.wallet('My finances')['cash'],100)
        storage.delete('My finances',refund);self.assertEqual(storage.wallet('My finances')['cash'],99.99)
        storage.delete('My finances',first);storage.delete('My finances',first)
        self.assertEqual(storage.wallet('My finances')['cash'],100)
    def test_batch_csv_and_cart_replay_are_persistent(self):
        rows=[dict(self.entry,kind='Expense')]
        self.assertEqual(save_batch('My finances',rows,True),1)
        self.assertEqual(save_batch('My finances',rows,True),0)
        self.assertEqual(storage.wallet('My finances')['cash'],99.99)
        frame=pd.DataFrame([dict(self.entry,description='Imported')])
        self.assertEqual(storage.import_csv('My finances',frame),1)
        self.assertEqual(storage.import_csv('My finances',frame),0)
        carts('My finances','Chai supplies',2.675);carts('My finances','Chai supplies',2.675)
        self.assertEqual(len(carts('My finances')),1);self.assertEqual(carts('My finances').iloc[0].amount,2.68)
    def test_request_payload_conflict_and_distinct_intent(self):
        kwargs=dict(workspace='My finances',day=self.today,amount=1,kind='Expense',category='Food',description='Chai',affects_cash=True,request_id='one')
        identifier=storage.add(**kwargs);self.assertEqual(storage.add(**kwargs),identifier)
        with self.assertRaises(ValueError):storage.add(**dict(kwargs,amount=2))
        storage.add(**dict(kwargs,request_id='two'))
        self.assertEqual(len(storage.read('My finances')),2);self.assertEqual(storage.wallet('My finances')['cash'],98)
    def test_concurrent_retries_do_not_duplicate_or_double_debit(self):
        def save(_):return storage.add('My finances',self.today,.005,'Expense','Food','Concurrent',affects_cash=True,request_id='concurrent')
        with ThreadPoolExecutor(max_workers=4) as pool:ids=list(pool.map(save,range(8)))
        self.assertEqual(len(set(ids)),1);self.assertEqual(len(storage.read('My finances')),1)
        self.assertEqual(storage.wallet('My finances')['cash'],99.99)
    def test_ai_uses_same_rounding_and_currency_policy(self):
        action={'type':'transaction','currency':'PKR',**self.entry}
        proposal=prepare('My finances',action,self.today)
        self.assertEqual(proposal['cash_after'],99.99)
        self.assertTrue(apply(proposal,'My finances',self.today));self.assertFalse(apply(proposal,'My finances',self.today))
        self.assertEqual(storage.wallet('My finances')['cash'],99.99)
        with self.assertRaises(ValueError):prepare('My finances',dict(action,description='USD lunch'),self.today)
    def test_invalid_batch_rolls_back_and_subcent_rows_sum_exactly(self):
        rows=[dict(self.entry,description=f'Purchase {i}') for i in range(3)]
        save_batch('My finances',rows,True)
        self.assertEqual(storage.wallet('My finances')['cash'],99.97)
        with self.assertRaises(ValueError):save_batch('My finances',rows+[dict(self.entry,currency='USD')],True)
        self.assertEqual(len(storage.read('My finances')),3);self.assertEqual(storage.wallet('My finances')['cash'],99.97)
    def test_foreign_upload_and_quick_note_have_no_save_form(self):
        from test_app import make_app,navigate
        app=make_app();navigate(app,'Receipt studio')
        app.session_state['receipt_details']={'text':'SHOP\nTOTAL $120','amount':120,'currency':'USD'}
        app.run();self.assertFalse(app.exception)
        self.assertFalse(any(w.label=='Save transaction' for w in app.button))
        navigate(app,'Cart & online orders')
        app.session_state['shopping_details']={'text':'SHOP\nTOTAL $120','amount':120,'currency':'USD'}
        app.run();self.assertFalse(app.exception)
        self.assertFalse(any(w.label=='Save planned cart' for w in app.button))


if __name__=='__main__':unittest.main()
