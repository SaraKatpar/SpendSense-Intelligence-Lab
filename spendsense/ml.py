"""Proposal models. No untrained predictions or silent algorithm substitutions."""

from pathlib import Path

import json

import numpy as np

import pandas as pd

import torch

from torch import nn
torch.set_num_threads(2)

import joblib

from storage import CATEGORIES, ROOT

from analytics import behavior_features, expenses



MODELS = ROOT/'models'



class SpendingLSTM(nn.Module):

    def __init__(self, n=len(CATEGORIES)):

        super().__init__()

        self.lstm = nn.LSTM(n,32,batch_first=True)

        self.head = nn.Linear(32,n)

    def forward(self,x):

        output,_ = self.lstm(x)

        return self.head(output[:,-1])



class TransactionAutoencoder(nn.Module):

    def __init__(self,n=len(CATEGORIES)+3):

        super().__init__()

        self.network=nn.Sequential(nn.Linear(n,16),nn.ReLU(),nn.Linear(16,4),nn.ReLU(),nn.Linear(4,16),nn.ReLU(),nn.Linear(16,n))

    def forward(self,x):

        return self.network(x)



def transaction_features(df):

    x=expenses(df)

    values=np.column_stack([np.log1p(x.amount.to_numpy()),x.date.dt.weekday.to_numpy()/6,x.date.dt.day.to_numpy()/31,

                            *[x.category.eq(c).astype(float).to_numpy() for c in CATEGORIES]])

    return x,values.astype(np.float32)



def daily_matrix(df, end=None):

    x=expenses(df)

    if x.empty:

        return pd.DataFrame(columns=CATEGORIES,dtype=float)

    end=pd.Timestamp(end or x.date.max()).normalize()

    x=x[x.date.le(end)]

    if x.empty:

        return pd.DataFrame(columns=CATEGORIES,dtype=float)

    matrix=x.pivot_table(index='date',columns='category',values='amount',aggfunc='sum',fill_value=0)

    return matrix.reindex(index=pd.date_range(x.date.min(),end),columns=CATEGORIES,fill_value=0).fillna(0)



def metadata(name):

    path=MODELS/f'{name}.json'

    return json.loads(path.read_text()) if path.exists() else None



def predict_category(text):

    path=MODELS/'categorizer'

    if not (path/'config.json').exists():

        return None

    from transformers import AutoTokenizer,AutoModelForSequenceClassification

    from nltk.tokenize import wordpunct_tokenize

    text=' '.join(wordpunct_tokenize(text.lower()))

    # Cached by the Streamlit caller; local artifacts only during app use.

    tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True)

    model=AutoModelForSequenceClassification.from_pretrained(path,local_files_only=True).eval()

    with torch.no_grad():

        probability=model(**tokenizer(text,return_tensors='pt',truncation=True,max_length=64)).logits.softmax(-1)[0]

    index=int(probability.argmax())

    return model.config.id2label[index],float(probability[index])



def forecast_days(df,today,horizon,model_directory=None):

    directory=Path(model_directory) if model_directory else MODELS

    if not 1<=int(horizon)<=365:raise ValueError('Forecast horizon must be 1–365 days.')

    if not (directory/'forecast.pt').exists():return None

    payload=torch.load(directory/'forecast.pt',map_location='cpu',weights_only=True)

    matrix=daily_matrix(df,pd.Timestamp(today)-pd.Timedelta(days=1))

    lookback=payload['lookback']

    if len(matrix)<lookback:return None

    model=SpendingLSTM().eval();model.load_state_dict(payload['state'])

    scale=np.array(payload['scale'],dtype=np.float32)

    history=(matrix.to_numpy(dtype=np.float32)/scale)[-lookback:]

    results=[]

    with torch.no_grad():

        for _ in range(int(horizon)):

            value=model(torch.tensor(history[None],dtype=torch.float32))[0].numpy().clip(0)

            results.append(value*scale);history=np.vstack([history[1:],value])

    return pd.DataFrame(results,index=pd.date_range(pd.Timestamp(today),periods=int(horizon)),columns=CATEGORIES)





def forecast(df,today):

    next_start=pd.Timestamp(today).normalize()+pd.offsets.MonthBegin(1)

    next_end=next_start+pd.offsets.MonthEnd(0)

    result=forecast_days(df,today,(next_end-pd.Timestamp(today)).days+1)

    if result is None:return None

    return result.loc[next_start:].sum(),next_start.strftime('%Y-%m')





def anomalies(df):

    if not (MODELS/'anomaly.pt').exists():

        return None

    payload=torch.load(MODELS/'anomaly.pt',map_location='cpu',weights_only=True)

    rows,features=transaction_features(df)

    if rows.empty:

        return rows

    values=(features-np.array(payload['mean']))/np.array(payload['scale'])

    model=TransactionAutoencoder().eval()

    model.load_state_dict(payload['state'])

    with torch.no_grad():

        error=((model(torch.tensor(values,dtype=torch.float32)).numpy()-values)**2).mean(axis=1)

    rows['Reconstruction error']=error

    return rows.loc[error>payload['threshold']].sort_values('Reconstruction error',ascending=False)



def persona(df,today):
    """Legacy deployment disabled. Research-only spending-mix model is separate."""
    return None
