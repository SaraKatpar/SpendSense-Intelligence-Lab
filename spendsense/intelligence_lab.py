"""SpendSense Intelligence Lab: student-first interface with transparent research mode."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import re
import pandas as pd
import streamlit as st
from storage import ROOT, CATEGORIES, read, add, wallet
from analytics import expenses

st.set_page_config(page_title='SpendSense | Intelligence Lab', page_icon='◈', layout='wide', initial_sidebar_state='expanded')
st.markdown('''<style>
.stApp{background:radial-gradient(circle at 90% 0%,#20193d 0%,#0c1020 45%,#090d18 100%);color:#e9e9fb}
[data-testid="stSidebar"]{background:#111427;border-right:1px solid #343051}
[data-testid="stMetric"]{background:#191c32;border:1px solid #353354;border-radius:18px;padding:17px}
[data-testid="stMetricValue"]{color:#80e8f1}
h1,h2,h3{letter-spacing:-.035em}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:#7956eb;color:white;border:0;border-radius:12px}
.lab-hero{padding:24px 28px;border:1px solid #453b76;border-radius:22px;background:linear-gradient(110deg,#2a2055,#122b40);margin-bottom:20px}
.lab-hero h1{margin:4px 0 6px;font-size:2.2rem}.lab-hero p{color:#bfc6e8;margin:0}
.lab-tag{color:#8fe4ed;font-size:.75rem;letter-spacing:.16em;font-weight:700}
</style>''', unsafe_allow_html=True)
TODAY=datetime.now(ZoneInfo('Asia/Karachi')).date()
PAGES_STUDENT=['Home HQ','Capture Studio','Future Lab','Spending DNA','Pattern Detective','Transactions']
PAGES_LAB=['Model Arena','Dataset Explorer','Experiment Console','Evaluation Report']
with st.sidebar:
    st.title('◈ SpendSense')
    st.caption('INTELLIGENCE LAB / V1')
    mode=st.radio('Experience',['Student Mode','ML Lab Mode'])
    workspace=st.selectbox('Workspace',['My finances','Household sample'],help='Household sample is historical INR research data; personal entries use PKR.')
    page=st.radio('Navigate',PAGES_STUDENT if mode=='Student Mode' else PAGES_LAB)
    st.divider()
    st.caption('Violet × Cyan · Local-first · No fabricated ML outputs')

@st.cache_data(ttl=60,show_spinner=False)
def load_data(name):
    return read(name)

def money(v):
    return f"{'INR' if workspace=='Household sample' else 'Rs.'} {v:,.0f}"

def heading(title, subtitle):
    st.markdown(f'<div class="lab-hero"><div class="lab-tag">SPENDSENSE / {mode.upper()}</div><h1>{title}</h1><p>{subtitle}</p></div>',unsafe_allow_html=True)

def artifact_status():
    base=ROOT/'models'
    return {
        'DistilBERT categorizer':any((base/p/'categorizer'/'config.json').exists() for p in ['research','personal','kaggle_categorizer']),
        'LSTM forecast':any((base/p/'forecast.pt').exists() for p in ['research','personal']),
        'Autoencoder anomaly detector':any((base/p/'anomaly.pt').exists() for p in ['research','personal']),
        'K-Means personas':False,
        'Tesseract OCR':__import__('shutil').which('tesseract') is not None,
    }

if workspace=='Household sample':
    sample=ROOT/'data'/'household_clean.csv'
    if sample.exists() and read(workspace).empty:
        from storage import import_csv
        records=pd.read_csv(sample,keep_default_na=False)
        records['description']=records.description.replace('','Unspecified expense')
        import_csv(workspace,records,request_id='household-initial-source-v1')

df=load_data(workspace)
exp=expenses(df)
if workspace=='Household sample':
    st.info('Research workspace: historical household transactions in INR. This is not Pakistani student data. Editing is disabled.')

if page=='Home HQ':
    heading('Your money, decoded.','One place for spending facts, emerging patterns and honest model insights.')
    a,b,c=st.columns(3)
    total_in=float(df.loc[df.kind.eq('Income'),'amount'].sum()) if not df.empty else 0
    total_out=float(exp.amount.sum()) if not exp.empty else 0
    cash=wallet(workspace)
    a.metric('Recorded expenses',money(total_out))
    b.metric('Recorded income',money(total_in))
    c.metric('Transactions',len(df))
    if cash is not None: st.caption('Wallet snapshot is available in the legacy app; transaction totals above are not a substitute for the current cash balance.')
    left,right=st.columns([3,2])
    with left:
        st.subheader('Where your money went')
        if exp.empty: st.info('No expenses yet. Start in Capture Studio.')
        else: st.bar_chart(exp.groupby('category').amount.sum().sort_values(ascending=False))
    with right:
        st.subheader('Intelligence feed')
        for name,ready in artifact_status().items():
            st.write(('🟢' if ready else '◌')+' '+name+(' — artifact detected' if ready else ' — not ready'))
        st.caption('Artifact detection does not guarantee that inference or evaluation succeeds.')
    st.subheader('Latest activity')
    st.dataframe(df.sort_values('date',ascending=False).head(8),hide_index=True,use_container_width=True)

elif page=='Capture Studio':
    heading('Capture Studio','Write an expense or scan a receipt. Confirm every field before saving.')
    if workspace=='Household sample':st.warning('Switch to My finances to save expenses.')
    else:
        method=st.radio('Capture method',['Smart text','Receipt photo','Manual'],horizontal=True)
        defaults={}
        if method=='Smart text':
            raw=st.text_area('Describe the expense',placeholder='Spent Rs. 450 on biryani')
            amount_match=re.search(r'(?:rs\.?|pkr)?\s*(\d+(?:\.\d{1,2})?)',raw,re.I)
            defaults={'description':raw,'amount':float(amount_match.group(1)) if amount_match else 0.0}
            st.caption('Amount is extracted by a simple rule, not an ML model. Category must be confirmed.')
        elif method=='Receipt photo':
            photo=st.file_uploader('Receipt image',type=['png','jpg','jpeg'])
            if photo and st.button('Extract receipt fields'):
                try:
                    from receipt_ocr import scan
                    st.session_state['ocr_fields']=scan(photo.getvalue())
                except Exception as exc:st.error(f'OCR unavailable: {exc}')
            fields=st.session_state.get('ocr_fields',{})
            defaults={'description':fields.get('merchant',''),'amount':fields.get('amount',0.0),'merchant':fields.get('merchant','')}
            st.caption('OCR needs Tesseract installed and permitted by your course requirements.')
        with st.form('review_and_save'):
            st.subheader('Review transaction')
            description=st.text_input('Description',value=defaults.get('description',''))
            merchant=st.text_input('Merchant',value=defaults.get('merchant',''))
            col1,col2,col3=st.columns(3)
            amount=col1.number_input('Amount (PKR)',min_value=0.0,value=float(defaults.get('amount',0.0)),step=50.0)
            day=col2.date_input('Date',value=TODAY,max_value=TODAY)
            kind=col3.selectbox('Type',['Expense','Income'])
            category=st.selectbox('Confirm category',CATEGORIES)
            save=st.form_submit_button('Save confirmed transaction',type='primary')
        if save:
            try:
                add(workspace,day,amount,kind,category,description,merchant,'receipt' if method=='Receipt photo' else 'manual',affects_cash=False)
                load_data.clear()
                st.success('Saved. Return to Home HQ to see your updated records.')
            except ValueError as exc:st.error(str(exc))

elif page=='Future Lab':
    heading('Future Lab','Real historical spending and forecast readiness — no invented predictions.')
    if exp.empty:st.info('Add transactions to see historical spending.')
    else:
        daily=exp.groupby(exp.date.dt.date).amount.sum().sort_index()
        st.line_chart(daily)
        st.metric('Observed daily average',money(float(daily.mean())))
    st.subheader('LSTM forecast')
    from ml import forecast_days
    import ml
    ml.MODELS=ROOT/'models'/('research' if workspace=='Household sample' else 'personal')
    if not (ml.MODELS/'forecast.pt').exists():st.warning('Trained LSTM artifact is missing. Forecast disabled until a validated model is restored or retrained.')
    else:
        try:
            predicted=forecast_days(df,TODAY,14)
            if predicted is None:st.info('Not enough supported data to forecast.')
            else:st.line_chart(predicted)
        except Exception as exc:st.error(f'Forecast could not run: {exc}')
    st.caption('An LSTM should be compared with a chronological naïve or seasonal baseline in Model Arena.')

elif page=='Spending DNA':
    heading('Spending DNA','Discover spending behavior without inventing personality labels.')
    if exp.empty:st.info('No spending history yet.')
    else:
        st.bar_chart(exp.groupby('category').amount.sum())
        st.write('Category shares are descriptive, not K-Means predictions.')
    st.warning('K-Means inference is not deployed. Cluster assignments and personas will appear after model, scaler and feature schema are validated.')

elif page=='Pattern Detective':
    heading('Pattern Detective','Investigate unusual spending; unusual does not mean fraudulent.')
    import ml
    ml.MODELS=ROOT/'models'/('research' if workspace=='Household sample' else 'personal')
    if not (ml.MODELS/'anomaly.pt').exists():st.warning('Autoencoder weights are missing; anomaly detection is not available yet.')
    else:
        try:
            result=ml.anomalies(df)
            if result is None or result.empty:st.info('No flagged transactions with the current model and threshold.')
            else:st.dataframe(result,use_container_width=True,hide_index=True)
        except Exception as exc:st.error(f'Anomaly model failed: {exc}')
    st.caption('Model thresholds and any human review labels must be evaluated separately.')

elif page=='Transactions':
    heading('Transactions','Your local financial records.')
    st.dataframe(df.sort_values('date',ascending=False),use_container_width=True,hide_index=True)

elif page=='Model Arena':
    heading('Model Arena','Compare ML components against honest baselines and inspect model readiness.')
    for name,ready in artifact_status().items():st.write(('🟢' if ready else '⚪')+' '+name+(' — files detected' if ready else ' — unavailable'))
    st.subheader('Existing evaluation records')
    reports=sorted((ROOT/'eval').glob('*/metrics.json'))
    if not reports:st.info('No evaluation metrics files found.')
    else:
        choice=st.selectbox('Experiment',reports,format_func=lambda p:p.parent.name)
        try:st.json(json.loads(choice.read_text(encoding='utf-8')))
        except Exception as exc:st.error(str(exc))
    st.caption('These are archived experiment records, not scores produced by this session. Different datasets and splits are not directly comparable.')

elif page=='Dataset Explorer':
    heading('Dataset Explorer','Know the provenance and limitations of every training dataset.')
    st.metric('Workspace records',len(df))
    if not df.empty:
        st.write('Columns:',', '.join(df.columns))
        st.dataframe(df.isna().sum().rename('missing').to_frame(),use_container_width=True)
        st.dataframe(df.head(20),hide_index=True,use_container_width=True)
    st.subheader('Local data sources')
    for path in sorted((ROOT/'data').glob('*')):
        if path.name!='spendsense.db':st.write(path.name+' / '+('folder' if path.is_dir() else 'file'))

elif page=='Experiment Console':
    heading('Experiment Console','A safe place to inspect model availability before inference.')
    st.write('Training is intentionally not triggered by page refresh.')
    st.dataframe(pd.DataFrame([{'component':name,'artifact_detected':ready} for name,ready in artifact_status().items()]),hide_index=True,use_container_width=True)
    st.info('Next build: connect validated inference adapters, versioned artifacts and reproducible benchmark runs.')

elif page=='Evaluation Report':
    heading('Evaluation Report','Inspect existing research documentation and reproducibility evidence.')
    reports=sorted((ROOT/'eval').glob('*/REPORT.md'))
    if reports:
        selected=st.selectbox('Research report',reports,format_func=lambda p:p.parent.name)
        st.markdown(selected.read_text(encoding='utf-8')[:35000])
    else:st.info('No evaluation reports found.')
    st.caption('Reports are historical records and should not be presented as fresh runs.')
