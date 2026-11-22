import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from sklearn.model_selection import train_test_split
from storage import ROOT
from ml import forecast_days
class KaggleTrainingTests(unittest.TestCase):
    def test_no_contradictory_classifier_labels_or_description_leakage(self):
        df=pd.read_csv(ROOT/'data/kaggle/categorizer_training.csv',keep_default_na=False);df=df[df.kind=='Expense']
        self.assertTrue((df.groupby('description').category.nunique()<=1).all())
        df=df[df.description.str.len()>=3].drop_duplicates('description');counts=df.category.value_counts();df=df[df.category.isin(counts[counts>=4].index)]
        train,test=train_test_split(df,test_size=.25,random_state=42,stratify=df.category)
        self.assertFalse(set(train.description)&set(test.description))
    def test_reference_does_not_assert_pkr_and_loads_trained_forecast(self):
        df=pd.read_csv(ROOT/'data/kaggle/personal_reference_clean.csv',keep_default_na=False);df.date=pd.to_datetime(df.date)
        self.assertEqual(set(df.currency),{'UNSPECIFIED_SOURCE_UNITS'});self.assertFalse(df.description.str.contains('credit card payment',case=False).any())
        result=forecast_days(df,df.date.max()+pd.Timedelta(days=1),14,ROOT/'models/kaggle_reference')
        self.assertEqual(result.shape,(14,9));self.assertTrue((result>=0).all().all())
