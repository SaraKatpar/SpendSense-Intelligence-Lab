import sys,tempfile,unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import storage,ml
from capture import parse_expenses,save_batch
from survival import scenario,projected_balances
class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.old=storage.DB;storage.DB=Path(self.temp.name)/'check.db'
        storage.save_wallet('me',5000,'2026-12-02',500,200,30,True)
    def tearDown(self):storage.DB=self.old;self.temp.cleanup()
    def test_natural_language_multiple_expenses_and_atomic_cash(self):
        rows=parse_expenses('Spent 350 on biryani and 150 on rickshaw yesterday.',date(2026,11,18),lambda text:('Food' if 'biryani' in text else 'Transport',.8))
        self.assertEqual([r['amount'] for r in rows],[350,150]);self.assertEqual(rows[0]['date'],date(2026,11,18));self.assertEqual(rows[1]['date'],date(2026,11,17))
        self.assertEqual(save_batch('me',rows,True),2);self.assertEqual(storage.wallet('me')['cash'],4500)
        bad=rows+[dict(rows[0],amount=-3)]
        with self.assertRaises(ValueError):save_batch('me',bad,True)
        self.assertEqual(len(storage.read('me')),2);self.assertEqual(storage.wallet('me')['cash'],4500)
    def test_parser_rejects_ambiguity_and_handles_iso_date(self):
        rows=parse_expenses('Paid 1,200 for internet on 2026-11-17',date(2026,11,18))
        self.assertEqual(rows[0]['amount'],1200)
        with self.assertRaises(ValueError):parse_expenses('2 burgers for 350',date(2026,11,18))
        with self.assertRaises(ValueError):parse_expenses('350 lunch 2026-11-20',date(2026,11,18))
    def test_delay_includes_newly_due_commitment_without_writing(self):
        storage.add_commitment('me','Fee',date(2026,12,3),700,'Education')
        p=storage.wallet('me');df=storage.read('me');ob=storage.commitments('me')
        original,_=scenario(p,df,ob,date(2026,11,18))
        delayed,plan=scenario(p,df,ob,date(2026,11,18),purchase=100,delay=5)
        self.assertEqual(original['reserved'],0);self.assertEqual(delayed['reserved'],700)
        self.assertEqual(delayed['days'],19);self.assertEqual(storage.wallet('me')['cash'],5000)
    def test_projection_counts_essentials_and_commitment_once(self):
        storage.add_commitment('me','Printing',date(2026,11,20),300,'Education')
        balances=projected_balances(storage.wallet('me'),storage.commitments('me'),date(2026,11,18),[10]*14)
        self.assertAlmostEqual(balances.iloc[-1],5000-14*(230+10)-300)
    def test_daily_lstm_horizon_and_no_future_leakage(self):
        df=pd.read_csv(storage.ROOT/'data/household_clean.csv');df.date=pd.to_datetime(df.date)
        today=df.date.max()+pd.Timedelta(days=1);directory=storage.ROOT/'models/research'
        prediction=ml.forecast_days(df,today,5,directory)
        self.assertEqual(prediction.shape,(5,9));self.assertTrue((prediction>=0).all().all())
        future=df.iloc[-1:].copy();future.date=today+pd.Timedelta(days=1);future.amount=999999
        changed=ml.forecast_days(pd.concat([df,future]),today,5,directory)
        pd.testing.assert_frame_equal(prediction,changed)
