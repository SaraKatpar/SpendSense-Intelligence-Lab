import sys,tempfile,unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import storage
from campus import runway

class CampusTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.old=storage.DB
        storage.DB=Path(self.folder.name)/'wallet.db'
        storage.save_wallet('student',6000,date(2026,12,2),500,180,20,False)
        storage.add_commitment('student','Trip home',date(2026,11,25),1500,'Transport')
    def tearDown(self):storage.DB=self.old;self.folder.cleanup()
    def state(self,**kwargs):return runway(storage.wallet('student'),storage.read('student'),storage.commitments('student'),date(2026,11,18),**kwargs)
    def test_cash_ceiling_protects_basics(self):
        result=self.state()
        self.assertEqual(result['days'],14)
        self.assertAlmostEqual(result['daily_cap'],4000/14)
        self.assertAlmostEqual(result['safe_purchase_max'],1200)
        planned=self.state(daily_optional=result['optional_cap'])
        self.assertAlmostEqual(planned['timeline']['Your chosen plan'].iloc[-1],500)
    def test_purchase_changes_capacity_and_never_creates_money(self):
        before=self.state();after=self.state(purchase=400)
        self.assertAlmostEqual(before['daily_cap']-after['daily_cap'],400/14)
        self.assertFalse(self.state(purchase=1201)['affordable'])
        self.assertAlmostEqual(self.state(purchase=1201)['essential_shortfall'],1)
        self.assertEqual(storage.wallet('student')['cash'],6000)
    def test_paid_commitment_is_not_counted_twice(self):
        before=self.state()
        identifier=int(storage.commitments('student').iloc[0].id)
        self.assertTrue(storage.pay_commitment('student',identifier,date(2026,11,18)))
        self.assertFalse(storage.pay_commitment('student',identifier,date(2026,11,18)))
        after=self.state()
        self.assertEqual(after['cash'],4500)
        self.assertEqual(after['reserved'],0)
        self.assertAlmostEqual(after['daily_cap'],before['daily_cap'])
        self.assertEqual(len(storage.read('student')),1)
    def test_receipt_expense_and_refund_accounting(self):
        storage.add('student','2026-11-18',350,'Expense','Food','Lunch',affects_cash=True)
        self.assertEqual(storage.wallet('student')['cash'],5650)
        identifier=int(storage.read('student').iloc[0].id)
        storage.delete('student',identifier)
        self.assertEqual(storage.wallet('student')['cash'],6000)
    def test_replacing_cash_snapshot_does_not_replay_old_expenses(self):
        storage.add('student','2026-11-18',350,'Expense','Food','Lunch',affects_cash=True)
        identifier=int(storage.read('student').iloc[0].id)
        storage.save_wallet('student',5000,date(2026,12,2),500,180,20)
        storage.delete('student',identifier)
        self.assertEqual(storage.wallet('student')['cash'],5000)
    def test_payday_expenses_are_in_next_cycle_and_overdue_are_reserved(self):
        storage.add_commitment('student','Next cycle fee','2026-12-02',999)
        storage.add_commitment('student','Overdue printing','2026-11-17',100)
        result=self.state()
        self.assertEqual(result['reserved'],1600)
        self.assertAlmostEqual(result['timeline'].iloc[0]['Current pace'],5700)
    def test_income_updates_cash_but_csv_import_does_not(self):
        storage.add('student','2026-11-18',200,'Income','Other','Refund',affects_cash=True)
        frame=pd.DataFrame([{'date':'2026-11-17','amount':100,'kind':'Expense','category':'Food','description':'Backfill'}])
        storage.import_csv('student',frame)
        self.assertEqual(storage.wallet('student')['cash'],6200)
    def test_deleting_recorded_commitment_reopens_reserve(self):
        identifier=int(storage.commitments('student').iloc[0].id)
        storage.pay_commitment('student',identifier,date(2026,11,18))
        transaction=int(storage.read('student').iloc[0].id)
        storage.delete('student',transaction)
        self.assertEqual(storage.wallet('student')['cash'],6000)
        self.assertEqual(self.state()['reserved'],1500)
    def test_displayed_spending_ceiling_never_rounds_up(self):
        from campus_ui import spend_limit
        self.assertEqual(spend_limit(267.857),'Rs. 267')
        self.assertEqual(spend_limit(-1),'Rs. 0')

if __name__=='__main__':unittest.main()
