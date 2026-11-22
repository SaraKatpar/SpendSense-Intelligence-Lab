"""Inspect the new Kaggle-trained candidates without cross-currency wallet inference."""
import json
import pandas as pd
import streamlit as st
from storage import ROOT
from ml import forecast_days

def render_kaggle_evidence():
    path=ROOT/'models/kaggle_evaluation.json'
    if not path.exists():return
    with st.expander('New Kaggle training results',expanded=True):
        report=json.loads(path.read_text());metrics=report['classification']['classification_report']
        a,b,c=st.columns(3)
        a.metric('New DistilBERT accuracy',f"{metrics['accuracy']:.1%}")
        b.metric('New DistilBERT macro-F1',f"{metrics['macro avg']['f1-score']:.3f}")
        c.metric('Clean personal expenses',report['reference_expenses'])
        st.caption('Legacy real-reference text/LSTM/autoencoder experiments. Spending-mix clusters were rebuilt separately from approved real references and remain research-only; shared classifier benchmarking is pending.')
        st.warning('Reference monetary units are unspecified in the personal source. These forecasts never substitute for your PKR wallet. The publisher describes real-world personal records; independent collection provenance is unverified.')
        sample=pd.read_csv(ROOT/'data/kaggle/personal_reference_clean.csv',keep_default_na=False);sample.date=pd.to_datetime(sample.date);anchor=sample.date.max()+pd.Timedelta(days=1)
        prediction=forecast_days(sample,anchor,14,ROOT/'models/kaggle_reference')
        if prediction is not None:
            st.markdown('**Fresh reference LSTM: 14 days after the source history**')
            st.line_chart(prediction.sum(axis=1).rename('Predicted daily expense — source units'))
            st.caption(f'Forecast anchored {anchor:%d %b %Y}; this is a historical reference scenario, not a forecast of your current balance.')
        st.write('You can opt into the new text classifier in My wallet → Settings. It is not promoted by default: different evaluation splits do not establish an improvement.')
        with st.expander('Full metrics and protocols'):st.json(report)
