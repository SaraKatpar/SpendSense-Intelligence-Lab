from datetime import date
from zoneinfo import ZoneInfo
from datetime import datetime
import re
import pandas as pd
import streamlit as st
from storage import CATEGORIES, add, read, budgets, set_budget, delete, import_csv
from analytics import expenses, weekly_mystery, recurring_payments
from receipt_ocr import scan
from ml import forecast, anomalies, persona, metadata, predict_category
import ml
from storage import ROOT
from campus_ui import render_runway,render_purchase,render_mission,render_prices,dataset_cards
from storage import wallet
from vibes import apply_vibes,reaction,apply_mood,campus_style,cozy_ui,dark_cafe,desk_style
from delight import delight_styles,show_celebration,receipt_polaroids

st.set_page_config(page_title='SpendSense · Campus finance',page_icon='◈',layout='wide')
st.markdown('''<style>
html,body,[class*="css"],.stApp {font-family:'Segoe UI',Arial,sans-serif;}
.stApp {background:#f7f4ec;color:#222638;}
[data-testid="stMainBlockContainer"] {padding-top:2.2rem!important;}
h1,h2,h3 {font-family:'Segoe UI',Arial,sans-serif!important;letter-spacing:-.035em;}
h1 {font-size:2.7rem!important;} [data-testid="stSidebar"] {background:#202333;}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] label {color:#f0edf8!important;}
[data-testid="stMetric"] {background:#fffdf8;border:1px solid #e6e0d4;border-radius:18px;padding:18px;}
[data-testid="stMetricValue"] {color:#6552c9;font-family:'Segoe UI',Arial,sans-serif;}
.eyebrow,.section-kicker {color:#7667a2;font-size:11px;letter-spacing:2px;font-weight:700;margin-top:12px;}
.hero {border:1px solid #d8d0eb;border-radius:20px;padding:24px;background:#eae5f7;margin:12px 0 24px;}
.hero h2 {margin:0;font-size:27px;} .hero p {color:#5a526f;margin-bottom:0;}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"] {background:#6a57ce;color:white;border:0;border-radius:12px;}
.runway-hero {display:flex;align-items:center;justify-content:space-between;gap:30px;background:#28243f;border-radius:25px;padding:32px 38px;color:#fff;margin:22px 0;}
.hero-kicker {font-size:11px;letter-spacing:2px;font-weight:700;opacity:.8;}
.runway-hero h2 {font-size:62px!important;color:#f7d77d;margin:5px 0;} .runway-hero h2 em {font-size:22px;color:#c5bddf;font-weight:400;font-style:normal;}
.runway-hero p {color:#d3cde2;font-size:14px;line-height:1.7;margin:0;}
.day-orbit {border:2px dashed #9180c8;border-radius:50%;min-width:142px;height:142px;display:flex;flex-direction:column;justify-content:center;align-items:center;}
.day-orbit strong {font-size:49px;color:#fff;} .day-orbit span {font-size:10px;letter-spacing:2px;color:#d2c3f8;}
.verdict,.pass-card {background:#e9e3f9;padding:30px;border-radius:22px;margin:10px 0 22px;}
.verdict.tight {background:#fae3d8;} .verdict.good {background:#dceee3;}
.verdict h2,.pass-card h2 {font-size:30px!important;margin:14px 0;}
.empty-wallet {background:#ece7f5;border-radius:24px;padding:42px;text-align:center;font-size:30px;} .empty-wallet p {font-size:15px;}
@media(max-width:700px) {.runway-hero{padding:22px;gap:12px}.runway-hero h2{font-size:40px!important}.day-orbit{min-width:94px;height:94px}.day-orbit strong{font-size:32px}}
div[data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:16px!important;}
</style>''',unsafe_allow_html=True)
today=datetime.now(ZoneInfo('Asia/Karachi')).date()
with st.sidebar:
    st.markdown('## ✳ SpendSense')
    st.markdown('<div class="sidebar-sticker">CHAI BREAK. BUDGET CHECK. ☕</div>',unsafe_allow_html=True)
    workspace=st.radio('Workspace',['My finances','Household sample'],help='Your finances start empty. Household sample contains real historical INR records.')
    sections={
        'My wallet':['Allowance runway','Overview','History','Settings'],
        'Add spending':['Cart & online orders','Receipt studio','Add transaction'],
        'Plan ahead':['Survival forecast','Can I say yes?','The weekend pass','Forecast & budgets','Grocery reality check'],
        'Insights':['AI chat','Spending coach','Unusual activity','Spending persona','Weekly mystery','Model lab']}
    def open_feature(group,target):
        st.session_state['main_section']=group
        st.session_state['section_page_'+group]=target
    quick_ai,quick_cart=st.columns(2)
    quick_ai.button('Talk to AI',on_click=open_feature,args=('Insights','AI chat'),use_container_width=True,type='primary')
    quick_cart.button('Upload cart',on_click=open_feature,args=('Add spending','Cart & online orders'),use_container_width=True)
    st.button('Spending limits & alerts',on_click=open_feature,args=('Insights','Spending coach'),use_container_width=True)
    section=st.radio('Explore',list(sections),key='main_section')
    page_labels={'Allowance runway':'Financial HQ','Add transaction':'Text & manual entry','Receipt studio':'Scan a receipt','Can I say yes?':'What-If Lab','Unusual activity':'Pattern Detective','Spending persona':'Spending mix','Model lab':'Research & model evidence'}
    page=st.selectbox('In this section',sections[section],key='section_page_'+section,format_func=lambda name:page_labels.get(name,name))
    st.caption({'My wallet':'Your balance and transaction record.','Add spending':'Receipts, online orders and quick entries.','Plan ahead':'Purchases, weekly plans and future costs.','Insights':'Spending patterns and model details.'}[section])
    st.divider()
    st.session_state['mood_theme']='Matcha'
    st.toggle('Meme reactions',value=True,key='meme_mode')
    float_enabled=st.toggle('Gentle animation',value=True,key='floating_stickers')
    st.toggle('Daily AI check-in',value=True,key='enable_checkin',help='Optional local Llama explanation; all financial and ML screens work without it.')
    st.caption(('INR' if workspace=='Household sample' else 'PKR')+' · Asia/Karachi')
    st.caption('Protect the basics. Romanticise the rest.')
from paper_theme import apply_theme,apply_student_dark
delight_styles()
apply_theme()
apply_student_dark()
st.markdown('<div class="paper-topline"><strong>SpendSense / '+section+'</strong><span>CAMPUS FINANCE · '+today.strftime('%d %b %Y')+'</span></div>',unsafe_allow_html=True)
show_celebration(workspace)
if st.session_state.get('active_workspace') != workspace:
    for state_key in ['manual_defaults','receipt_details','shopping_details','shopping_bought']:
        st.session_state.pop(state_key,None)
    st.session_state['entry_version']=st.session_state.get('entry_version',0)+1
    st.session_state['active_workspace']=workspace
if workspace=='Household sample':
    sample_path=ROOT/'data/household_clean.csv'
    if sample_path.exists() and read(workspace).empty:
        records=pd.read_csv(sample_path,keep_default_na=False)
        records['description']=records.description.replace('','Unspecified expense')
        import_csv(workspace,records,request_id='household-initial-source-v1')
    st.caption('RESEARCH SAMPLE · Historical single-household data in INR. No currency conversion. Names and categories are normalised for the proposal.')
df=read(workspace)
if workspace!='Household sample':
    from coach import brief
    brief(df,workspace,today)
if workspace=='Household sample' and not df.empty:
    today=(df.date.max()+pd.Timedelta(days=1)).date()
ml.MODELS=ROOT/'models'/({'My finances':'personal','Household sample':'research'}[workspace])
# Text classification transfers labels, but money models stay with their currency/data source.
if workspace!='Household sample' and not (ml.MODELS/'categorizer').exists():
    categorizer_path=ROOT/'models'/'research'
else:categorizer_path=ml.MODELS
if st.session_state.get('categorizer_choice')=='Kaggle-trained candidate' and (ROOT/'models/kaggle_categorizer/categorizer/config.json').exists():
    categorizer_path=ROOT/'models/kaggle_categorizer'
x=expenses(df)
st.markdown('<div class="vibe-ribbon"><span>✳ CAMPUS MODE</span><span>CANTEEN • CLASS • CHAI</span><span>HOSTEL WALLET CLUB</span></div>',unsafe_allow_html=True)
if page not in ['Allowance runway','Can I say yes?','The weekend pass','Grocery reality check','Survival forecast','AI chat','Spending coach']:
    st.markdown('<div class="eyebrow">SPENDSENSE CAMPUS · YOUR EXPENSES, EXPLAINED</div>',unsafe_allow_html=True)
    st.title(page if page!='Overview' else 'Where did it go?')

def money(v):return f"{'INR' if workspace=='Household sample' else 'Rs.'} {v:,.0f}"

def show_provenance(name):
    original=ml.MODELS
    if name=='categorizer':ml.MODELS=categorizer_path
    try:info=metadata(name)
    finally:ml.MODELS=original
    if info:
        st.caption(f"{info['architecture']} · Training data: {info['data']}")
    return info

@st.cache_data(show_spinner=False)
def categorise_global(text, model_directory):
    original=ml.MODELS
    try:
        ml.MODELS=model_directory
        return predict_category(text)
    finally:ml.MODELS=original

def categorise(text,model_directory):
    from app.personalization import predict
    return predict(workspace,text,categorise_global(text,model_directory))

def entry_form(prefix, defaults=None, source='manual'):
    if workspace=='Household sample':
        st.info('This reference dataset is read-only. Switch to Demo or My finances to add a transaction.')
        return
    defaults=defaults or {}
    from app.finance import enforce_currency
    try:enforce_currency(workspace,defaults.get('currency'),defaults.get('text',''))
    except ValueError as error:st.error(str(error));return
    with st.form(prefix):
        a,b=st.columns(2)
        description=a.text_input('Description',value=defaults.get('text','')[:300],key=prefix+'description')
        merchant=b.text_input('Merchant (optional)',value=defaults.get('merchant',''),key=prefix+'merchant')
        a,b,c=st.columns(3)
        amount=a.number_input('Amount ('+('INR' if workspace=='Household sample' else 'PKR')+')',min_value=0.0,value=float(defaults.get('amount',0)),step=50.0,key=prefix+'amount')
        day=b.date_input('Date',value=min(defaults.get('date') or today,today),max_value=today,key=prefix+'date')
        kind=c.selectbox('Type',['Expense','Income'],key=prefix+'kind')
        category=st.selectbox('Confirm category',CATEGORIES,index=CATEGORIES.index(defaults.get('category','Other')),key=prefix+'category')
        update_cash=st.checkbox('Update my current cash with this entry',value=wallet(workspace) is not None,key=prefix+'cash',help='Uncheck when this payment is already included in the cash snapshot you entered. CSV imports never change the snapshot.')
        st.caption('Review every field before saving. Suggested categories and receipt fields may be wrong.')
        save=st.form_submit_button('Save transaction',type='primary')
    if save:
        try:
            from app.finance import operation_key
            nonce=st.session_state.get('separate_intent_'+prefix)
            request_id=operation_key('form',{'nonce':nonce,'day':day,'amount':amount,'kind':kind,'category':category,'description':description,'merchant':merchant,'cash':update_cash})[0] if nonce else None
            add(workspace,day,amount,kind,category,description,merchant,source,affects_cash=update_cash,currency=defaults.get('currency'),text=defaults.get('text',''),request_id=request_id)
            st.success('Transaction saved. Check Allowance runway for the updated plan, or History for the entry.')
        except ValueError as error:st.error(str(error))
    if st.button('Start a separate identical purchase',key=prefix+'separate'):
        import uuid
        st.session_state['separate_intent_'+prefix]=uuid.uuid4().hex
        st.info('A new purchase is ready. Review its fields and press Save transaction. Repeated Save clicks still record it once.')

if page=='Allowance runway':render_runway(workspace,df,today)
elif page=='Can I say yes?':
    render_purchase(workspace,df,today)
    from survival import render_scenarios
    render_scenarios(workspace,df,today)
elif page=='The weekend pass':render_mission(workspace,df,today)
elif page=='Grocery reality check':render_prices(today)
elif page=='Settings':
    if workspace=='Household sample':st.info('This reference workspace is read-only.')
    else:
        from campus_ui import wallet_editor
        wallet_editor(workspace,today,expanded=True)
        st.selectbox('Categorization model',['Proposal reference','Kaggle-trained candidate'],key='categorizer_choice',help='The candidate was retrained on cleaned Kaggle descriptions. Scores use different splits; it is not claimed to outperform the reference. Only text classification changes; monetary models stay isolated.')
        st.caption('Appearance and optional AI check-in controls are in the sidebar. Settings apply to the selected workspace; refreshing your balance replaces its previous cash snapshot.')
elif page=='Survival forecast':
    from survival import render_survival
    render_survival(workspace,df,today)
elif page=='AI chat':
    from ai_chat import render_chat
    render_chat(df,workspace,today)
elif page=='Cart & online orders':
    from shopping import render_shopping
    render_shopping(workspace,today,entry_form)
elif page=='Spending coach':
    from coach import render_coach
    render_coach(df,workspace,today)
elif page=='Overview':
    st.markdown('<div class="hero"><h2>A little perspective goes a long way.</h2><p>See what changed, spot repeating payments, and find the story behind your spending.</p></div>',unsafe_allow_html=True)
    month=st.date_input('Month to explore',today, key='overview_month').strftime('%Y-%m')
    current=df[df.date.dt.strftime('%Y-%m').eq(month)]
    spending=expenses(current).amount.sum();income=current[current.kind.eq('Income')].amount.sum()
    a,b,c=st.columns(3)
    a.metric('Money in',money(income));b.metric('Money out',money(spending));c.metric('Recorded net',money(income-spending))
    st.caption('Recorded net is income minus expenses in this month; it is not a verified bank balance.')
    left,right=st.columns([1.5,1])
    with left:
        st.subheader('Where it went')
        if not expenses(current).empty:st.bar_chart(expenses(current).groupby('category').amount.sum(),color='#bfe68f')
        else:st.info('Add a transaction to begin your spending story.')
    with right:
        st.subheader('On repeat')
        recurring=recurring_payments(df)
        if recurring:st.dataframe(pd.DataFrame(recurring),hide_index=True)
        else:st.caption('No consistent recurring payments found. At least three similar payments are needed.')
    st.subheader('Spending over time')
    if not x.empty:st.line_chart(x.groupby('date').amount.sum(),color='#bfe68f')
elif page=='Add transaction':
    from capture import render_text_capture
    render_text_capture(workspace,today,lambda text:categorise(text,categorizer_path))
    st.write('A short note is enough to get started. You stay in control of the final entry.')
    note=st.text_input('Quick note',placeholder='Lunch at the cafe Rs. 350')
    if st.button('Suggest details'):
        result=categorise(note,categorizer_path) if note.strip() else None
        match=re.search(r'(?:rs\.?|pkr)\s*([\d,]+(?:\.\d{1,2})?)',note,re.I)
        from app.finance import currency_of
        defaults={'text':note,'amount':float(match.group(1).replace(',','')) if match else 0,'currency':currency_of(note)}
        if result:
            defaults['category']=result[0];st.info(f'Suggested category: {result[0]} · model confidence {result[1]:.0%}. Please confirm.')
        else:st.info('No trained categorizer is available yet. Choose the category manually.')
        st.session_state['manual_defaults']=defaults
        # A new form key loads the latest suggestion without overwriting user edits.
        st.session_state['entry_version']=st.session_state.get('entry_version',0)+1
    entry_form('manual'+str(st.session_state.get('entry_version',0)),st.session_state.get('manual_defaults'))
    show_provenance('categorizer')
elif page=='Receipt studio':
    st.write('Photograph → extract → review → save. Your receipt stays on this computer.')
    reaction('receipt')
    def process_receipt(content):
        try:
            with st.spinner('Reading the receipt…'):
                details=scan(content)
                result=categorise(details['text'],categorizer_path)
                if result:details['category']=result[0]
                st.session_state['receipt_details']=details
                st.session_state['receipt_version']=st.session_state.get('receipt_version',0)+1
        except Exception as error:st.error(str(error))
    upload=st.file_uploader('Upload a receipt',type=['png','jpg','jpeg'])
    if upload:
        st.image(upload,width=320)
        if st.button('Read receipt',type='primary'):
            process_receipt(upload.getvalue())
    if 'receipt_details' in st.session_state:
        details=st.session_state['receipt_details']
        with st.expander('Extracted text'):st.text(details['text'])
        st.warning('Check the total, date and merchant. Receipt layouts and ambiguous dates can cause extraction errors.')
        expected_currency='INR' if workspace=='Household sample' else 'PKR'
        foreign=details.get('currency') and details['currency']!=expected_currency
        if foreign:
            st.warning(f"Receipt appears to use {details['currency']}; this workspace uses {expected_currency}. No exchange-rate conversion is performed.")
        entry_form('receipt'+str(st.session_state.get('receipt_version',0)),details,'receipt')
elif page=='Forecast & budgets':
    st.write('Plan next month using category forecasts and budgets you choose.')
    show_provenance('forecast')
    result=forecast(df,today)
    next_month=(pd.Timestamp(today)+pd.offsets.MonthBegin(1)).strftime('%Y-%m')
    existing=budgets(workspace,next_month)
    with st.expander(f'Set category budgets · {next_month}',expanded=result is None):
        st.caption('Use 0 for categories without a budget limit. Forecast warnings apply to positive limits.')
        with st.form('budgets'):
            values={c:st.number_input(c,min_value=0.0,value=float(existing.get(c,0)),step=100.0) for c in CATEGORIES}
            if st.form_submit_button('Save budgets'):
                for category,value in values.items():set_budget(workspace,next_month,category,value)
                existing=values;st.success('Budgets saved.')
    if result:
        predictions,month=result
        chart=pd.DataFrame({'Forecast':predictions,'Budget':[existing.get(c,0) for c in predictions.index]})
        st.subheader(f'Next month · {month}');st.bar_chart(chart)
        st.metric('Forecast total',money(predictions.sum()))
        for category,value in predictions.items():
            if existing.get(category,0)>0 and value>existing[category]:st.warning(f'{category}: forecast {money(value)} exceeds your {money(existing[category])} budget.')
        st.caption('Recursive LSTM estimate, not a guarantee. Missing transaction days are treated as zero spending; incomplete records can distort results.')
    else:st.info('Forecast requires a trained LSTM and at least 14 days of recorded expense history.')
elif page=='Unusual activity':
    st.write('A second look at transactions that differ from the patterns learned by the model.')
    show_provenance('anomaly')
    result=anomalies(df)
    if result is None:st.info('Train the autoencoder to enable unusual-transaction alerts.')
    elif result.empty:st.success('No transactions exceeded the current reconstruction-error threshold.')
    else:
        reaction('anomaly')
        st.dataframe(result[['date','description','category','amount','Reconstruction error']],hide_index=True)
        st.caption('These transactions exceeded the model’s reconstruction-error threshold. Unusual does not mean fraudulent; large legitimate purchases may appear here.')
        from intelligence import explain_anomalies
        explain_anomalies(df,result)
elif page=='Spending persona':
    st.subheader('Your recorded spending mix')
    if not x.empty:
        totals=x.groupby('category').amount.sum()
        st.bar_chart(totals/totals.sum())
        st.caption('Shares of your recorded expenses. This is a descriptive summary, not a fitted cluster or identity.')
    else:st.info('Add expenses to see their category shares.')
    st.info('The rebuilt spending-mix clusters are research-only. Berka-trained artifacts are not loaded into this app.')
elif page=='Weekly mystery':
    reaction('mystery')
    st.markdown('<div class="hero"><h2>⌕ Case file: the spending jump</h2><p>Follow the clues. Pick your suspect. Reveal the evidence.</p></div>',unsafe_allow_html=True)
    case=weekly_mystery(df,today)
    if case:
        st.caption(f"Two complete weeks compared · case week {case['start']} – {case['end']}")
        st.subheader('Which category had the largest increase?')
        choice=st.radio('Choose your suspect',case['options'],horizontal=True)
        if st.button('Reveal the evidence',type='primary'):
            if choice==case['answer']:st.success('Case solved. You followed the right trail!')
            else:st.info(f"A plot twist: the biggest increase was {case['answer']}.")
            a,b,c=st.columns(3)
            a.metric('Previous week',money(case['previous']));b.metric('Case week',money(case['current']));c.metric('Increase',money(case['increase']))
            unit='purchase' if case['count']==1 else 'purchases'
            st.write(f"{case['count']} recorded {case['answer'].lower()} {unit} contributed to this week’s total.")
            st.caption('Evidence comes from recorded expenses. It establishes a spending change, not the reason you made the purchases.')
    else:st.info('No case to investigate yet. We need two complete weeks with at least three expenses each and a category increase.')
elif page=='History':
    st.write('Your transaction record, with an export whenever you need it.')
    if workspace!='Household sample':
        with st.expander('Import a transaction CSV'):
            imported=st.file_uploader('CSV file',type=['csv'])
            st.caption('Columns: date, amount, kind, category, description; optional merchant and currency. Use this workspace’s currency. Repeated identical imports are ignored.')
            if imported:
                try:
                    incoming=pd.read_csv(imported)
                    st.dataframe(incoming.head(),hide_index=True)
                    if st.button('Import these transactions'):
                        total=import_csv(workspace,incoming)
                        st.success(f'Imported {total} transactions.');st.rerun()
                except (ValueError,TypeError) as error:st.error(str(error))
    if not df.empty:
        receipt_polaroids(df,'INR' if workspace=='Household sample' else 'PKR')
        selected=st.multiselect('Categories',CATEGORIES,default=CATEGORIES)
        filtered=df[df.category.isin(selected)]
        st.dataframe(filtered[['id','date','description','merchant','kind','category','amount','source']].sort_values('date',ascending=False),hide_index=True)
        export=filtered.copy()
        export['user_id']=workspace
        export['currency']='INR' if workspace=='Household sample' else 'PKR'
        st.download_button('Export CSV',export.to_csv(index=False).encode(),'spendsense-transactions.csv','text/csv')
        if workspace!='Household sample':
            with st.expander('Correct a category and remember it for my account'):
                target=st.selectbox('Entry to correct',df.id.tolist(),format_func=lambda i:f"{i} · {df.loc[df.id.eq(i),'description'].iloc[0]}")
                corrected=st.selectbox('Change category to',CATEGORIES)
                if st.button('Apply category correction'):
                    from storage import correct_category
                    correct_category(workspace,target,corrected)
                    st.success('Category corrected for your account. Cash is unchanged.');st.rerun()
        with st.expander('Remove a mistaken entry'):
            identifier=st.selectbox('Transaction ID',df.id.tolist())
            confirm=st.checkbox('Remove this transaction permanently')
            if st.button('Delete selected entry',disabled=not confirm or workspace=='Household sample'):
                delete(workspace,identifier);st.rerun()
    else:st.info('No transactions yet. Add your first one from the sidebar.')
elif page=='Model lab':
    from kaggle_ui import render_kaggle_evidence
    render_kaggle_evidence()
    evaluation_path=ROOT/'models/evaluation_report.json'
    if evaluation_path.exists():
        import json
        with st.expander('Reproduced model evaluation and limitations',expanded=True):st.json(json.loads(evaluation_path.read_text()))
    dataset_cards()
    st.write('The models behind your insights, with training provenance and evaluation results.')
    for name,title in [('categorizer','DistilBERT categorisation'),('forecast','LSTM forecast'),('anomaly','Autoencoder alerts'),('ocr_evaluation','Receipt extraction evaluation')]:
        with st.expander(title):
            original=ml.MODELS
            if name=='categorizer':ml.MODELS=categorizer_path
            try:info=metadata(name)
            finally:ml.MODELS=original
            if info:st.json(info)
            else:st.info('Not trained yet. See the project guide for the training command and required data.')
    st.caption('Receipt extraction uses OpenCV and Tesseract. Recurring payments and Weekly Mystery use transparent rules; they are not additional ML models.')

from ai_chat import maybe_checkin
if st.session_state.get('enable_checkin',True):maybe_checkin(df,workspace,today,page)
