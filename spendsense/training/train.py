"""Train proposal components from approved real reference CSVs only.

Real CSV columns: date, amount, kind, category, description, merchant, user_id.
The same currency must be used throughout. Never merge different users into a series.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import json
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import joblib
from storage import CATEGORIES
from analytics import behavior_features
from ml import MODELS,SpendingLSTM,TransactionAutoencoder,daily_matrix,transaction_features

torch.set_num_threads(2)
torch.manual_seed(42)

def save_meta(name,values):
    (MODELS/f'{name}.json').write_text(json.dumps(values,indent=2))

def fit_network(model,x,y,epochs):
    optimizer=torch.optim.Adam(model.parameters(),lr=.003)
    loss_fn=nn.MSELoss()
    x,y=torch.tensor(x,dtype=torch.float32),torch.tensor(y,dtype=torch.float32)
    for _ in range(epochs):
        model.train()
        for indices in torch.randperm(len(x)).split(64):
            optimizer.zero_grad()
            loss=loss_fn(model(x[indices]),y[indices])
            loss.backward()
            optimizer.step()
    return model.eval()

def train_forecast(df,epochs,provenance):
    groups=[]
    for _,group in df.groupby('user_id'):
        matrix=daily_matrix(group)
        # Exclude last 20% chronologically for validation.
        if len(matrix)>=75:
            groups.append(matrix.to_numpy(dtype=np.float32))
    if not groups:
        raise ValueError('Forecasting needs at least 75 dated days for a single identified user.')
    scale=np.maximum(np.mean(np.concatenate([g[:int(len(g)*.8)] for g in groups]),axis=0),1)
    train_x,train_y,test_x,test_y,baseline=[],[],[],[],[]
    for group in groups:
        values=group/scale
        split=int(len(values)*.8)
        for i in range(14,len(values)):
            if i<split:
                train_x.append(values[i-14:i]);train_y.append(values[i])
            else:
                test_x.append(values[i-14:i]);test_y.append(values[i]);baseline.append(values[i-7:i].mean(axis=0))
    model=fit_network(SpendingLSTM(),np.array(train_x),np.array(train_y),epochs)
    with torch.no_grad():
        predicted=model(torch.tensor(np.array(test_x),dtype=torch.float32)).numpy().clip(0)*scale
    actual=np.array(test_y)*scale
    totals_actual=[];totals_predicted=[];totals_baseline=[]
    for group in groups:
        split=int(len(group)*.8)
        if len(group)-split<30:continue
        history=group[split-14:split]/scale
        horizon=[]
        with torch.no_grad():
            for _ in range(30):
                value=model(torch.tensor(history[None],dtype=torch.float32))[0].numpy().clip(0)
                horizon.append(value*scale)
                history=np.vstack([history[1:],value])
        totals_actual.append(group[split:split+30].sum(axis=0))
        totals_predicted.append(np.sum(horizon,axis=0))
        totals_baseline.append(group[split-7:split].mean(axis=0)*30)
    recursive_metrics={}
    if totals_actual:
        recursive_metrics={'recursive_30_day_category_total_mae':float(abs(np.array(totals_predicted)-np.array(totals_actual)).mean()),
                           'baseline_30_day_category_total_mae':float(abs(np.array(totals_baseline)-np.array(totals_actual)).mean()),
                           'recursive_evaluation':'First 30 validation days per eligible household; no future observations fed back'}
    torch.save({'state':model.state_dict(),'scale':scale.tolist(),'lookback':14},MODELS/'forecast.pt')
    save_meta('forecast',{'architecture':'PyTorch LSTM','data':provenance,'validation':'chronological final 20% per user; rolling one-day predictions',
                         'rmse':float(np.sqrt(((predicted-actual)**2).mean())),
                         'mae':float(abs(predicted-actual).mean()),'baseline_mae':float(abs(np.array(baseline)*scale-actual).mean()),
                         **recursive_metrics,'caution':'Validation is on the supplied dataset only; no accuracy claim for other households or currencies.'})

def train_anomaly(df,epochs,provenance):
    _,values=transaction_features(df.sort_values('date'))
    if len(values)<50:
        raise ValueError('Anomaly training requires at least 50 expenses.')
    split=int(len(values)*.8)
    mean=values[:split].mean(axis=0);scale=np.maximum(values[:split].std(axis=0),.01)
    normalized=(values-mean)/scale
    model=fit_network(TransactionAutoencoder(),normalized[:split],normalized[:split],epochs)
    with torch.no_grad():
        errors=((model(torch.tensor(normalized[split:])).numpy()-normalized[split:])**2).mean(axis=1)
    threshold=float(np.quantile(errors,.95))
    torch.save({'state':model.state_dict(),'mean':mean.tolist(),'scale':scale.tolist(),'threshold':threshold},MODELS/'anomaly.pt')
    save_meta('anomaly',{'architecture':'PyTorch autoencoder','data':provenance,'threshold':threshold,
                       'validation':'95th percentile of held-out reconstruction error; no fraud labels or detection-accuracy claim'})

def train_personas(df,provenance):
    raise ValueError('Use training/build_spending_mix.py: audited real-source research only.')

def train_categorizer(df,epochs,provenance):
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    # Deduplicate before splitting so repeated merchant phrases don't leak.
    x=df[df.kind.eq('Expense') & df.description.str.len().ge(3)][['description','category']].drop_duplicates('description')
    counts=x.category.value_counts()
    x=x[x.category.isin(counts[counts>=4].index)]
    if len(x)<30 or x.category.value_counts().min()<2:
        raise ValueError('Categorisation needs at least 30 unique labelled descriptions and at least two per category.')
    train,test=train_test_split(x,test_size=.25,random_state=42,stratify=x.category)
    local_base=Path(__file__).resolve().parents[1]/'models'/'base-distilbert'
    base=str(local_base) if (local_base/'model.safetensors').exists() else 'distilbert/distilbert-base-uncased'
    tokenizer=AutoTokenizer.from_pretrained(base)
    model=AutoModelForSequenceClassification.from_pretrained(base,num_labels=len(CATEGORIES),
        id2label=dict(enumerate(CATEGORIES)),label2id={c:i for i,c in enumerate(CATEGORIES)})
    # Keep the full DistilBERT architecture, but fine-tune its final two blocks
    # and classification head to fit an 8 GB laptop without GPU dependencies.
    for parameter in model.distilbert.parameters():parameter.requires_grad=False
    for layer in model.distilbert.transformer.layer[-2:]:
        for parameter in layer.parameters():parameter.requires_grad=True
    optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=2e-5)
    counts=train.category.value_counts()
    weights=torch.tensor([np.sqrt(len(train)/max(int(counts.get(c,0)),1)) for c in CATEGORIES],dtype=torch.float32)
    loss_fn=nn.CrossEntropyLoss(weight=weights/weights.mean())
    model.train()
    training_loss=[]
    for epoch in range(epochs):
        shuffled=train.sample(frac=1,random_state=42)
        epoch_loss=[]
        for i in range(0,len(shuffled),4):
            batch=shuffled.iloc[i:i+4]
            encoded=tokenizer(batch.description.tolist(),padding=True,truncation=True,max_length=64,return_tensors='pt')
            logits=model(**encoded).logits
            loss=loss_fn(logits,torch.tensor([CATEGORIES.index(c) for c in batch.category]))
            optimizer.zero_grad();loss.backward();optimizer.step()
            epoch_loss.append(float(loss.detach()))
        training_loss.append(float(np.mean(epoch_loss)))
        print(f'Epoch {epoch+1}/{epochs}: training loss {training_loss[-1]:.4f}',flush=True)
    model.eval();predictions=[]
    with torch.no_grad():
        for text in test.description:
            prediction=model(**tokenizer(text,return_tensors='pt',truncation=True,max_length=64)).logits.argmax(-1).item()
            predictions.append(CATEGORIES[prediction])
    path=MODELS/'categorizer';model.save_pretrained(path);tokenizer.save_pretrained(path)
    save_meta('categorizer',{'architecture':'Fine-tuned DistilBERT','data':provenance,'train_rows':len(train),'test_rows':len(test),'epochs':epochs,
                            'loss':'Cross entropy with square-root inverse class frequency from training split',
                            'training_loss':training_loss,
                            'fine_tuning':'Final two DistilBERT encoder blocks plus classification head; earlier blocks and embeddings frozen',
                            'max_tokens':64,
                            'labels':CATEGORIES,'confusion_matrix':confusion_matrix(test.category,predictions,labels=CATEGORIES).tolist(),
                            'report':classification_report(test.category,predictions,output_dict=True,zero_division=0)})

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--csv',required=True)
    parser.add_argument('--model',choices=['all','forecast','anomaly','personas','categorizer'],default='all')
    parser.add_argument('--epochs',type=int,default=10)
    parser.add_argument('--output',default=str(MODELS))
    args=parser.parse_args()
    if args.model=='personas':
        parser.error('Use training/build_spending_mix.py for spending-mix clusters.')
    from training.real_source_policy import require_real_csv
    require_real_csv(args.csv)
    df=pd.read_csv(args.csv,keep_default_na=False)
    required={'date','amount','kind','category','description','merchant','user_id'}
    if not required.issubset(df.columns):
        raise ValueError(f'Missing columns: {sorted(required-set(df.columns))}')
    df['date']=pd.to_datetime(df.date,errors='raise').dt.normalize()
    df['amount']=pd.to_numeric(df.amount,errors='raise')
    if df[list(required)].isna().any().any() or not np.isfinite(df.amount).all() or (df.amount<=0).any() or not df.category.isin(CATEGORIES).all() or not df.kind.isin(['Expense','Income']).all():
        raise ValueError('Training rows contain missing or invalid values; clean them first.')
    global_models=Path(args.output)
    globals()['MODELS']=global_models
    MODELS.mkdir(exist_ok=True,parents=True)
    provenance=str(Path(args.csv).name)
    for name,fn in [('forecast',train_forecast),('anomaly',train_anomaly),('categorizer',train_categorizer)]:
        if args.model in ('all',name):
            print(f'Training {name}...',flush=True)
            if name in ('personas',):fn(df,provenance)
            else:fn(df,args.epochs,provenance)
            print(f'Saved {name}.',flush=True)

if __name__=='__main__':main()
