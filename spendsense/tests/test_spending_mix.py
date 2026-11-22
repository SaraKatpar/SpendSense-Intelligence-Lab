"""Real-source reconstruction and deployment isolation, no model/test-set scoring."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data.spending_mix import FEATURES, profile
from training.real_source_policy import require_real_csv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'eval/spending_mix_v1'


class SpendingMixTests(unittest.TestCase):
    def test_features_reconstruct_and_currency_scale_invariant(self):
        records = pd.read_csv(ROOT/'data/household_clean.csv')
        records.date = pd.to_datetime(records.date)
        rows = records.loc[records.kind.eq('Expense')]
        saved = pd.read_csv(OUT/'profiles.csv').query("source=='household'").iloc[0]
        expected = profile(rows, saved.window_start, saved.window_end, records.date.min(), records.date.max())
        scaled = rows.copy(); scaled.amount *= 150.37
        changed = profile(scaled, saved.window_start, saved.window_end, records.date.min(), records.date.max())
        np.testing.assert_allclose([expected[f] for f in FEATURES], saved[FEATURES].to_numpy(dtype=float))
        np.testing.assert_allclose([changed[f] for f in FEATURES], [expected[f] for f in FEATURES])
        self.assertAlmostEqual(sum(expected[f] for f in FEATURES[:3]), 1.)

    def test_eligibility_never_imputes_short_or_sparse_windows(self):
        frame = pd.read_csv(ROOT/'data/household_clean.csv'); frame.date = pd.to_datetime(frame.date)
        saved = pd.read_csv(OUT/'profiles.csv').query("source=='household'").iloc[0]
        rows = frame.loc[frame.kind.eq('Expense') & frame.date.between(saved.window_start, saved.window_end)]
        self.assertIsNone(profile(rows.iloc[:19], saved.window_start, saved.window_end, frame.date.min(), frame.date.max()))
        self.assertIsNone(profile(rows, saved.window_start, saved.window_end, pd.Timestamp(saved.window_start)+pd.Timedelta(days=1), frame.date.max()))
        sparse = rows.loc[rows.date.dt.month.isin([pd.Timestamp(saved.window_start).month])]
        self.assertIsNone(profile(sparse, saved.window_start, saved.window_end, frame.date.min(), frame.date.max()))

    def test_no_test_accounts_and_no_pseudousers(self):
        data = pd.read_csv(OUT/'profiles.csv')
        split = pd.read_csv(ROOT/'eval/berka_accounts/proposed_account_split.csv')
        train = set(split.loc[split.partition.eq('train'), 'account_id'])
        ids = data.loc[data.source.eq('berka'), 'entity_id'].str.removeprefix('berka_').astype(int)
        self.assertTrue(set(ids) <= train)
        self.assertEqual(data.loc[data.source.eq('household'), 'entity_id'].nunique(), 1)
        self.assertEqual(data.loc[data.source.eq('personal_reference'), 'entity_id'].nunique(), 1)
        np.testing.assert_allclose(data.groupby('entity_id').weight.sum(), 1.)
        self.assertTrue(data.debit_rows.ge(20).all()); self.assertTrue(data.active_months.ge(5).all())

    def test_protected_berka_artifacts_unchanged(self):
        proof = json.loads((OUT/'protected_berka_hashes.json').read_text())
        for name, digest in proof.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest, name)

    def test_training_policy_and_retirement(self):
        self.assertEqual(require_real_csv(ROOT/'data/household_clean.csv'), (ROOT/'data/household_clean.csv').resolve())
        with self.assertRaises(ValueError): require_real_csv(ROOT/'data/campus_demo_training.csv')
        with self.assertRaises(ValueError): require_real_csv(ROOT/'data/student_profiles_synthetic.csv')
        for name in ('data/campus_demo_training.csv', 'data/student_profiles_synthetic.csv', 'models/campus', 'models/demo'):
            self.assertFalse((ROOT/name).exists())

    def test_research_models_not_in_app(self):
        from student_styles import student_style
        from ml import persona
        self.assertIsNone(student_style(None, None)); self.assertIsNone(persona(None, None))
        source = (ROOT/'app.py').read_text(encoding='utf-8')
        self.assertNotIn('seed_campus(', source); self.assertNotIn('seed(today)', source)
        self.assertNotIn("joblib.load", (ROOT/'mobile/api.py').read_text())


if __name__=='__main__': unittest.main()
