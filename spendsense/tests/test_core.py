import os
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import storage
from analytics import weekly_mystery,recurring_payments
from receipt_ocr import extract_fields

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.previous=storage.DB
        storage.DB=Path(self.folder.name)/'test.db'
    def tearDown(self):
        storage.DB=self.previous
        self.folder.cleanup()
    def test_workspace_isolation_and_validation(self):
        storage.add('Demo','2026-11-01',100,'Expense','Food','Lunch')
        self.assertEqual(len(storage.read('Demo')),1)
        self.assertTrue(storage.read('My finances').empty)
        for value in [0,-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):storage.add('Demo','2026-11-01',value,'Expense','Food','Lunch')
        identifier=storage.read('Demo').iloc[0].id
        storage.delete('My finances',identifier)
        self.assertEqual(len(storage.read('Demo')),1)
    def test_mystery_ignores_partial_week_and_income(self):
        for day in ['2026-11-03','2026-11-04','2026-11-05']:
            storage.add('Demo',day,100,'Expense','Food','Lunch')
        for day in ['2026-11-10','2026-11-11','2026-11-12']:
            storage.add('Demo',day,200,'Expense','Food','Lunch')
        storage.add('Demo','2026-11-17',99999,'Expense','Shopping','Ignore partial week')
        storage.add('Demo','2026-11-12',99999,'Income','Other','Ignore income')
        result=weekly_mystery(storage.read('Demo'),date(2026,11,17))
        self.assertEqual(result['answer'],'Food')
        self.assertEqual(result['increase'],300)
    def test_recurring_requires_consistent_cadence_and_amount(self):
        for day in ['2026-08-05','2026-09-05','2026-10-05']:
            storage.add('Demo',day,1000,'Expense','Bills','Internet','Provider')
        found=recurring_payments(storage.read('Demo'))
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]['Typical amount'],1000)
    def test_receipt_total_is_not_subtotal(self):
        result=extract_fields('MY SHOP\n17/11/2026\nSUBTOTAL 900.00\nTAX 100.00\nTOTAL Rs 1,000.00')
        self.assertEqual(result['amount'],1000)
        self.assertEqual(result['date'],date(2026,11,17))
    def test_rounded_receipt_and_short_year(self):
        result=extract_fields('customer name\nMR D.I.Y. SDN BHD\n12-01-19\nTOTAL RM 33,92\nTOTAL ROUNDED RM 33,90')
        self.assertEqual(result['merchant'],'MR D.I.Y. SDN BHD')
        self.assertEqual(result['amount'],33.9)
        self.assertEqual(result['date'],date(2019,1,12))
    def test_import_is_atomic(self):
        frame=pd.DataFrame([{'date':'2026-11-01','amount':100,'kind':'Expense','category':'Food','description':'Lunch'},
                            {'date':'2026-11-02','amount':-20,'kind':'Expense','category':'Food','description':'Invalid'}])
        with self.assertRaises(ValueError):storage.import_csv('My finances',frame)
        self.assertTrue(storage.read('My finances').empty)
        self.assertEqual(storage.import_csv('My finances',frame.iloc[:1]),1)

if __name__=='__main__':unittest.main()
