import sys,tempfile,unittest
from pathlib import Path
from datetime import date,timedelta
from unittest.mock import patch
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import storage
from app.personalization import predict,corrected_prediction
from ai_chat import propose_change
from chat_actions import prepare,apply


class PersonalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=storage.DB;storage.DB=Path(self.tmp.name)/'learn.db'
        self.today=date.fromisoformat(storage.cash_day())
        storage.save_wallet('My finances',1000,self.today+timedelta(days=14),0,0,0)
        self.identifier=storage.add('My finances',self.today,100,'Expense','Other','Corner cafe lunch',affects_cash=True)
    def tearDown(self):storage.DB=self.old;self.tmp.cleanup()
    def test_correction_persists_and_is_user_scoped(self):
        storage.correct_category('My finances',self.identifier,'Food',request_id='review-one')
        self.assertEqual(predict('My finances','CORNER café lunch',('Shopping',.9))[0],'Food')
        self.assertEqual(predict('another','Corner cafe lunch',('Shopping',.9))[0],'Shopping')
        self.assertEqual(storage.wallet('My finances')['cash'],900)
        self.assertEqual(storage.read('My finances').iloc[0].category,'Food')
        storage.correct_category('My finances',self.identifier,'Food',request_id='review-one')
        with storage.connect() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM category_corrections').fetchone()[0],1)
    def test_latest_label_wins_even_after_changing_back(self):
        for category in ['Food','Groceries','Food','Groceries']:
            storage.correct_category('My finances',self.identifier,category)
            self.assertEqual(predict('My finances','Corner cafe lunch',('Other',.8))[0],category)
        self.assertEqual(storage.wallet('My finances')['cash'],900)
    @patch('ai_chat.requests.post')
    def test_change_to_x_is_reviewed_before_learning(self,post):
        action=propose_change('change to Food',self.today,workspace='My finances')
        proposal=prepare('My finances',action,self.today)
        self.assertEqual(proposal['target_description'],'Corner cafe lunch')
        self.assertEqual(predict('My finances','Corner cafe lunch',('Other',.8))[0],'Other')
        self.assertTrue(apply(proposal,'My finances',self.today));self.assertFalse(apply(proposal,'My finances',self.today))
        self.assertEqual(predict('My finances','Corner cafe lunch',('Other',.8))[0],'Food');post.assert_not_called()
    def test_cross_user_correction_and_unknown_label_rejected(self):
        with self.assertRaises(ValueError):storage.correct_category('another',self.identifier,'Food')
        with self.assertRaises(ValueError):storage.correct_category('My finances',self.identifier,'Invented')
        self.assertEqual(storage.read('My finances').iloc[0].category,'Other')
    def test_unrelated_text_abstains_and_review_same_category_can_learn(self):
        storage.correct_category('My finances',self.identifier,'Other')
        self.assertEqual(predict('My finances','Corner cafe lunch',('Shopping',.8))[0],'Other')
        self.assertEqual(corrected_prediction('railway train ticket',('Transport',.8),[{'description':'Corner cafe lunch','category':'Food'}])[0],'Transport')
    def test_learning_curve_uses_only_earlier_real_labels(self):
        root=Path(__file__).resolve().parents[1]
        frame=pd.read_csv(root.parent/'work/category_benchmark_v1/development.csv')
        for source,rows in frame.groupby('source'):
            self.assertLess(rows.loc[rows.partition.eq('train'),'date'].max(),rows.loc[rows.partition.eq('correction'),'date'].min())
            self.assertLess(rows.loc[rows.partition.eq('correction'),'date'].max(),rows.loc[rows.partition.eq('curve_evaluation'),'date'].min())
        curves=pd.read_csv(root/'eval/personalization_v1/learning_curve.csv')
        self.assertTrue(curves.actual_corrections.le(curves.requested_corrections).all())
        self.assertTrue(curves.groupby('source').evaluation_rows.nunique().eq(1).all())
        zero=curves.loc[curves.requested_corrections.eq(0)]
        self.assertTrue(zero.global_accuracy.eq(zero.personalized_accuracy).all())


if __name__=='__main__':unittest.main()
