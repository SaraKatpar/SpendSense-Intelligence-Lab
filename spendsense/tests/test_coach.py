import sys,unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from coach import assess
class CoachTests(unittest.TestCase):
    def test_repeated_breaches_and_exclusions(self):
        rows=[(1,'2026-11-16',600,'Expense','Food','Canteen lunch'),(2,'2026-11-17',500,'Expense','Food','Chai cafe'),(3,'2026-11-18',100,'Expense','Food','Dinner'),(4,'2026-11-19',9999,'Expense','Food','Chai'),(5,'2026-11-18',9000,'Income','Food','Chai'),(6,'2026-11-18',999,'Expense','Groceries','Tea'),(7,'2026-11-10',1200,'Expense','Food','Restaurant')]
        df=pd.DataFrame(rows,columns=['id','date','amount','kind','category','description']);df['merchant']='';df.date=pd.to_datetime(df.date)
        r=assess(df,{'category':'Eating out','cap':1000},date(2026,11,18))
        self.assertEqual(r['spent'],1200);self.assertEqual(len(r['breaches']),2);self.assertEqual(r['over'],200);self.assertEqual(len(r['previous']),1)
    def test_exact_limit_is_not_breach(self):
        df=pd.DataFrame([{'id':1,'date':pd.Timestamp('2026-11-18'),'amount':1000,'kind':'Expense','category':'Shopping','description':'Shoes','merchant':''}])
        r=assess(df,{'category':'Shopping','cap':1000},date(2026,11,18))
        self.assertTrue(r['breaches'].empty);self.assertEqual(r['remaining'],0)
