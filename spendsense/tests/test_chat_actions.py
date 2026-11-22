import sys,tempfile,unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import storage
from chat_actions import prepare,apply
from ai_chat import propose_change

class ActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=storage.DB
        storage.DB=Path(self.tmp.name)/'test.db';self.today=date(2026,11,19)
        storage.save_wallet('My finances',5000,'2026-12-01',500,200,50,True)
        self.action={'type':'transaction','currency':'PKR','date':str(self.today),'amount':350,'kind':'Expense','category':'Food','description':'Lunch'}
    def tearDown(self):storage.DB=self.old;self.tmp.cleanup()
    def test_preview_and_once_only_cash_update(self):
        p=prepare('My finances',self.action,self.today)
        self.assertEqual(len(storage.read('My finances')),0)
        self.assertTrue(apply(p,'My finances',self.today));self.assertFalse(apply(p,'My finances',self.today))
        self.assertEqual(storage.wallet('My finances')['cash'],4650)
        self.assertEqual(len(storage.read('My finances')),1)
    def test_stale_and_cross_workspace(self):
        p=prepare('My finances',self.action,self.today)
        with self.assertRaises(ValueError):apply(p,'Demo',self.today)
        storage.add('My finances',self.today,20,'Expense','Food','Chai')
        with self.assertRaises(ValueError):apply(p,'My finances',self.today)
        self.assertEqual(storage.wallet('My finances')['cash'],5000)
    def test_wallet_preserves_other_settings_and_limit(self):
        p=prepare('My finances',{'type':'wallet','currency':'PKR','field':'cash','value':4200},self.today)
        apply(p,'My finances',self.today)
        self.assertEqual(storage.wallet('My finances')['food_daily'],200)
        self.assertEqual(storage.wallet('My finances')['complete_history'],1)
        p=prepare('My finances',{'type':'weekly_limit','currency':'PKR','category':'Eating out','amount':1000},self.today)
        apply(p,'My finances',self.today)
        from coach import rules
        self.assertEqual(rules('My finances').iloc[0]['cap'],1000)
    def test_reject_bad_model_data(self):
        for change in ({'amount':float('nan')},{'amount':.004},{'currency':'USD'},{'workspace':'Demo'},{'date':'2027-01-01'},{'category':'Fake'}):
            with self.subTest(change=change),self.assertRaises(ValueError):prepare('My finances',{**self.action,**change},self.today)
        with self.assertRaises(ValueError):prepare('Household sample',self.action,self.today)
    @patch('ai_chat.requests.post')
    def test_structured_extraction(self,post):
        post.return_value=Mock();post.return_value.json.return_value={'message':{'content':'{"action":null}'}}
        self.assertIsNone(propose_change('Set my weekly food limit to 1000',self.today))
        self.assertEqual(post.call_args.kwargs['json']['format'],'json')
        post.reset_mock()
        self.assertIsNone(propose_change('What if I log 350 for lunch?',self.today))
        self.assertIsNone(propose_change('I have 5000 left',self.today))
        post.assert_not_called()

    def test_review_ui_saves_only_on_apply(self):
        from streamlit.testing.v1 import AppTest
        code="""from datetime import date
from storage import read
from ai_chat import chat_body
chat_body(read('My finances'),'My finances',date(2026,11,19))
"""
        with patch('ai_chat.model_status',return_value=True),patch('ai_chat.propose_change',return_value=self.action):
            app=AppTest.from_string(code,default_timeout=30).run()
            app.chat_input[0].set_value('Log Rs 350 for lunch today').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(storage.read('My finances')),0)
            next(b for b in app.button if b.label=='Apply account change').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(storage.wallet('My finances')['cash'],4650)
            self.assertEqual(len(storage.read('My finances')),1)
