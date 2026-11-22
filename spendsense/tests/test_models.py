import sys
import unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import numpy as np
import torch
import ml
from storage import CATEGORIES

class ModelTests(unittest.TestCase):
    def test_architecture_shapes(self):
        self.assertEqual(tuple(ml.SpendingLSTM()(torch.zeros(2,14,len(CATEGORIES))).shape),(2,len(CATEGORIES)))
        self.assertEqual(tuple(ml.TransactionAutoencoder()(torch.zeros(2,len(CATEGORIES)+3)).shape),(2,len(CATEGORIES)+3))
    def test_daily_matrix_does_not_include_future_or_income(self):
        rows=pd.DataFrame([{'date':pd.Timestamp('2026-11-01'),'kind':'Expense','category':'Food','amount':100},
                           {'date':pd.Timestamp('2026-11-03'),'kind':'Expense','category':'Food','amount':200},
                           {'date':pd.Timestamp('2026-11-01'),'kind':'Income','category':'Other','amount':99999}])
        matrix=ml.daily_matrix(rows,date(2026,11,2))
        self.assertEqual(len(matrix),2)
        self.assertEqual(matrix.to_numpy().sum(),100)
        self.assertTrue(ml.daily_matrix(rows,date(2026,10,31)).empty)
    def test_missing_artifact_is_explicit(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            previous=ml.MODELS;ml.MODELS=Path(directory)
            try:self.assertIsNone(ml.forecast(pd.DataFrame(),date(2026,11,17)))
            finally:ml.MODELS=previous

if __name__=='__main__':unittest.main()
