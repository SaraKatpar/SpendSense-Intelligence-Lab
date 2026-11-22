"""Evaluate the freshly trained Kaggle candidates, separately from PKR models."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from storage import ROOT
from training.evaluate_models import evaluate_forecast,evaluate_anomaly,evaluate_classifier

def main():
    data=ROOT/'data/kaggle';reference=pd.read_csv(data/'personal_reference_clean.csv',keep_default_na=False);reference.date=pd.to_datetime(reference.date)
    text=pd.read_csv(data/'categorizer_training.csv',keep_default_na=False);text.date=pd.to_datetime(text.date)
    report={'sources':['https://www.kaggle.com/datasets/entrepreneurlife/personal-finance','https://www.kaggle.com/datasets/soumojit11/daily-household-transactions'],'source_units':'Personal data currency not recorded explicitly; not used for PKR inference','reference_expenses':len(reference),'classification':evaluate_classifier(text,ROOT/'models/kaggle_categorizer'),'forecast':evaluate_forecast(reference,ROOT/'models/kaggle_reference'),'anomaly':evaluate_anomaly(reference,ROOT/'models/kaggle_reference'),'clustering':json.loads((ROOT/'eval/spending_mix_v1/metrics.json').read_text()),'deployment_decision':'Existing default classifiers and PKR models retained. New text classifier is an explicit opt-in research candidate. No cross-currency monetary model substitution.','limitations':['Publisher describes personal records as real-world; collection provenance not independently verified.','One individual history is not a student population.','Zero-filled spending days assume logging coverage; coverage is not independently verified.','New classifier split differs from the original, so its score is not a head-to-head improvement claim.','No verified anomaly labels; threshold flags are not fraud accuracy.']}
    (ROOT/'models/kaggle_evaluation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Classifier accuracy',report['classification']['classification_report']['accuracy'],'macro F1',report['classification']['classification_report']['macro avg']['f1-score'])
    print('Forecast',report['forecast']);print('Saved models/kaggle_evaluation.json')
if __name__=='__main__':main()
