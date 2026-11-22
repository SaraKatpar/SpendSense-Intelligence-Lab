"""Re-evaluate saved proposal artifacts without retraining or inventing scores.
Run from project: python training/evaluate_models.py --classifier
"""
import sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pandas as pd,torch,joblib
from sklearn.metrics import classification_report,confusion_matrix,adjusted_rand_score,silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.base import clone
from storage import ROOT,CATEGORIES
from ml import daily_matrix,SpendingLSTM,TransactionAutoencoder,transaction_features

torch.set_num_threads(2)

def evaluate_forecast(df,directory):
    p=torch.load(directory/'forecast.pt',weights_only=True,map_location='cpu');model=SpendingLSTM().eval();model.load_state_dict(p['state']);scale=np.array(p['scale'],dtype=np.float32)
    xs=[];ys=[];baselines=[]
    for _,group in df.groupby('user_id'):
        matrix=daily_matrix(group).to_numpy(dtype=np.float32);split=int(len(matrix)*.8)
        for i in range(max(split,p['lookback']),len(matrix)):
            xs.append(matrix[i-p['lookback']:i]/scale);ys.append(matrix[i]);baselines.append(matrix[i-7:i].mean(axis=0))
    with torch.no_grad():predicted=model(torch.tensor(np.array(xs),dtype=torch.float32)).numpy().clip(0)*scale
    actual=np.array(ys);base=np.array(baselines)
    return {'protocol':'rolling one-day chronological final 20%, observed past days allowed; not a free-running multi-day evaluation','test_days':len(xs),'mae':float(abs(predicted-actual).mean()),'rmse':float(np.sqrt(((predicted-actual)**2).mean())),'baseline_7day_mae':float(abs(base-actual).mean()),'baseline_7day_rmse':float(np.sqrt(((base-actual)**2).mean()))}


def evaluate_classifier(df,directory):
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    x=df[df.kind.eq('Expense')&df.description.str.len().ge(3)][['description','category']].drop_duplicates('description')
    counts=x.category.value_counts();x=x[x.category.isin(counts[counts>=4].index)]
    _,test=train_test_split(x,test_size=.25,random_state=42,stratify=x.category)
    model=AutoModelForSequenceClassification.from_pretrained(directory/'categorizer',local_files_only=True).eval();tokenizer=AutoTokenizer.from_pretrained(directory/'categorizer',local_files_only=True)
    predicted=[]
    with torch.no_grad():
        for start in range(0,len(test),8):
            inputs=tokenizer(test.description.iloc[start:start+8].tolist(),padding=True,truncation=True,max_length=64,return_tensors='pt')
            predicted.extend(model.config.id2label[int(i)] for i in model(**inputs).logits.argmax(-1))
    return {'protocol':'reconstruct original deduplicated description stratified 25% split, seed 42; no new independent test set','test_rows':len(test),'classification_report':classification_report(test.category,predicted,output_dict=True,zero_division=0),'labels':CATEGORIES,'confusion_matrix':confusion_matrix(test.category,predicted,labels=CATEGORIES).tolist()}


def evaluate_anomaly(df,directory):
    p=torch.load(directory/'anomaly.pt',weights_only=True,map_location='cpu');rows,features=transaction_features(df.sort_values('date'));cut=int(len(features)*.8)
    x=(features[cut:]-np.array(p['mean']))/np.array(p['scale']);model=TransactionAutoencoder().eval();model.load_state_dict(p['state'])
    with torch.no_grad():error=((model(torch.tensor(x,dtype=torch.float32)).numpy()-x)**2).mean(axis=1)
    return {'protocol':'original calibration final 20%, not an untouched anomaly test set','rows':len(error),'threshold':p['threshold'],'flag_rate':float((error>p['threshold']).mean()),'error_quantiles':dict(zip(['p50','p90','p95','p99'],np.quantile(error,[.5,.9,.95,.99]).tolist())),'precision_recall':'Not estimable: dataset has no verified anomaly labels.'}


def evaluate_styles():
    return json.loads((ROOT/'eval/spending_mix_v1/metrics.json').read_text(encoding='utf-8'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--classifier',action='store_true');args=parser.parse_args();report={}
    for name,csv in [('research','household_clean.csv')]:
        frame=pd.read_csv(ROOT/'data'/csv,keep_default_na=False);frame.date=pd.to_datetime(frame.date);directory=ROOT/'models'/name
        report[name]={'forecast':evaluate_forecast(frame,directory),'anomaly':evaluate_anomaly(frame,directory)}
        print(name+' forecast/anomaly evaluated',flush=True)
        if args.classifier and name=='research':report[name]['classifier']=evaluate_classifier(frame,directory);print('DistilBERT evaluated',flush=True)
    report['spending_mix_clusters']=evaluate_styles()
    output=ROOT/'models/evaluation_report.json'
    if output.exists() and not args.classifier:
        old=json.loads(output.read_text());previous=old.get('research',{}).get('classifier')
        if previous:report['research']['classifier']=previous
    output.write_text(json.dumps(report,indent=2));print('Saved',output,flush=True)
if __name__=='__main__':main()
