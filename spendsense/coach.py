"""Explainable local spending coach. No remote model or financial-data upload."""
import re
import pandas as pd
import streamlit as st
from storage import connect,CATEGORIES
from app.finance import money,enforce_currency

EATING_OUT=r'\b(?:chai|tea|coffee|cafe|café|canteen|restaurant|takeaway|takeout|delivery|foodpanda|pizza|burger|dinner|lunch|breakfast|eating out)\b'

def rules(workspace,label=None,category=None,cap=None):
    if label is not None:
        enforce_currency(workspace,text=label)
        cap=money(cap,True)
    with connect() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS coach_rules(workspace TEXT,label TEXT,category TEXT,cap REAL,PRIMARY KEY(workspace,label))')
        if label is not None:
            conn.execute('INSERT OR REPLACE INTO coach_rules VALUES(?,?,?,?)',(workspace,label,category,float(cap)))
        return pd.read_sql_query('SELECT label,category,cap FROM coach_rules WHERE workspace=?',conn,params=(workspace,))

def assess(df,rule,today):
    end=pd.Timestamp(today).normalize()
    start=end-pd.Timedelta(days=end.weekday())
    rows=df[(df.kind=='Expense') & (df.date<=end)].copy()
    if rule['category']=='Eating out':
        text=rows.description.fillna('')+' '+rows.merchant.fillna('')
        rows=rows[(rows.category=='Food') & text.str.contains(EATING_OUT,case=False,regex=True)]
    else:rows=rows[rows.category==rule['category']]
    rows=rows.sort_values(['date','id'])
    current=rows[rows.date>=start].copy()
    current['running_total']=current.amount.cumsum()
    breaches=current[current.running_total>float(rule['cap'])]
    previous=[]
    for offset in (1,2,3):
        week=start-pd.Timedelta(weeks=offset)
        spent=float(rows[(rows.date>=week)&(rows.date<week+pd.Timedelta(days=7))].amount.sum())
        if spent>float(rule['cap']):previous.append({'week':week,'spent':spent})
    spent=float(current.amount.sum())
    return {'spent':spent,'remaining':max(0,float(rule['cap'])-spent),'over':max(0,spent-float(rule['cap'])),'breaches':breaches,'previous':previous,'rows':current,'start':start}

def brief(df,workspace,today):
    saved=rules(workspace)
    for rule in saved.to_dict('records'):
        result=assess(df,rule,today)
        if result['over']:
            st.warning(f"Coach · {rule['label']}: Rs. {result['spent']:,.0f} logged against Rs. {rule['cap']:,.0f} this week. {len(result['breaches'])} purchase(s) crossed or continued above the limit. Open Insights → Spending coach.")

def render_coach(df,workspace,today):
    st.title('Your spending coach')
    st.write('Set a boundary. Spot the repeat. Make the next purchase a choice.')
    st.caption('Local, rule-based coaching uses your recorded purchases. Existing ML category suggestions feed the transaction record; these limit alerts are calculations, not an AI prediction. No inbox or bank monitoring.')
    if workspace=='Household sample':st.info('Use My finances to set personal limits.');return
    with st.form('coach_rule'):
        category=st.selectbox('Habit to watch',['Eating out']+CATEGORIES)
        cap=st.number_input('Weekly limit (PKR)',min_value=1.0,value=1000.0,step=100.0)
        st.caption('Weeks run Monday–Sunday. Eating out matches Food entries mentioning chai, cafés, canteens, restaurants or meals. Check matched entries below; missing descriptions can hide purchases.')
        if st.form_submit_button('Set my habit limit'):
            rules(workspace,category,category,cap);st.success('Limit saved. It applies to this week’s existing entries too.')
    saved=rules(workspace)
    if saved.empty:st.info('Start with one habit, like eating out. Your coach will check it whenever you open the app.');return
    for rule in saved.to_dict('records'):
        result=assess(df,rule,today)
        with st.container(border=True):
            st.subheader(rule['label'])
            a,b=st.columns(2)
            a.metric('Logged this week',f"Rs. {result['spent']:,.0f}")
            b.metric('Weekly limit',f"Rs. {rule['cap']:,.0f}")
            st.progress(min(1.,result['spent']/rule['cap']))
            count=len(result['breaches'])
            if count>1:
                st.warning(f"Repeat flag: {count} purchases crossed or continued above your weekly limit. You are Rs. {result['over']:,.0f} over.")
            elif count:st.warning(f"Your weekly limit was crossed. You are Rs. {result['over']:,.0f} over.")
            elif result['spent']>=rule['cap']*.8:st.info(f"Getting close: Rs. {result['remaining']:,.0f} left for this week.")
            else:st.success(f"Rs. {result['remaining']:,.0f} left under this limit, based on logged spending.")
            if result['previous']:st.write(f"This limit was also exceeded in {len(result['previous'])} of the previous 3 completed weeks, when applying your current limit retrospectively.")
            with st.expander('Show the purchases behind this advice'):
                st.dataframe(result['rows'][['date','description','merchant','amount','running_total']],hide_index=True)
                st.caption('A purchase that first crosses the limit counts once; each later purchase above it is another flag. No-spend days are not flags. Future entries and income are excluded.')
            prompt=st.selectbox('Ask your coach',['What is happening?','What can I do next?','Why did you flag this?'],key='coach_ask_'+rule['label'])
            if prompt=='What is happening?':st.write(f"You have logged Rs. {result['spent']:,.0f} for {rule['label'].lower()} since {result['start']:%d %b}. " + ('The repeated purchases are keeping the total above your chosen boundary.' if count>1 else 'Keep logging purchases so this picture stays useful.'))
            elif prompt=='What can I do next?':st.write('Pause the next optional purchase, choose a lower-cost plan, or revise the limit if it was unrealistic. Check your allowance runway before moving money away from meals, travel or your emergency reserve.' if count else f"You have Rs. {result['remaining']:,.0f} remaining under this limit. Check your runway too: a category limit is not extra cash.")
            else:st.write(f"I added the matching expense entries this week and compared their running total with Rs. {rule['cap']:,.0f}. Your records show {count} purchases above that boundary. These are repeat spending flags, not separate notifications or proof of a complete spending history.")
            if st.button('Remove this limit',key='remove_coach_'+rule['label']):
                with connect() as conn:conn.execute('DELETE FROM coach_rules WHERE workspace=? AND label=?',(workspace,rule['label']))
                st.rerun()
