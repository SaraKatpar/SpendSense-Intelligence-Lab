"""Conservative multi-expense extraction with mandatory review and atomic saving."""
import re,math
from datetime import date,timedelta
import pandas as pd
import streamlit as st
from storage import CATEGORIES,connect,cash_day,wallet
from storage import validated_entry,insert_entry
from app.finance import enforce_currency,replay,receipt


def parse_expenses(text,today,classify=None,workspace='My finances'):
    text=text.strip()
    if not text:raise ValueError('Enter an expense note first.')
    if re.search(r'\btomorrow\b|\bday before yesterday\b',text,re.I):
        raise ValueError('Use an exact YYYY-MM-DD date for that relative date; future purchases belong in planning.')
    currency=enforce_currency(workspace,text=text)
    chunks=re.split(r'\s+and\s+(?=(?:(?:today|yesterday)\s+)?(?:(?:spent|paid|bought)\s+)?(?:Rs\.?\s*|PKR\s*)?\d)|;|\n',text,flags=re.I)
    rows=[]
    for chunk in chunks:
        chunk=chunk.strip(' .')
        if not chunk:continue
        matches=re.findall(r'\b20\d{2}-\d{2}-\d{2}\b|\btoday\b|\byesterday\b',chunk,flags=re.I)
        days={today if m.lower()=='today' else today-timedelta(days=1) if m.lower()=='yesterday' else date.fromisoformat(m) for m in matches}
        if len(days)>1:raise ValueError('Conflicting dates in one expense. Put one date beside each amount.')
        day=next(iter(days)) if days else today
        if day>today:raise ValueError('This is a future plan. Use the simulator or save a planned cart instead.')
        chunk=re.sub(r'\b20\d{2}-\d{2}-\d{2}\b|\b(today|yesterday)\b','',chunk,flags=re.I)
        numbers=list(re.finditer(r'(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?(?![\w.])',chunk))
        if len(numbers)!=1:raise ValueError('Use one amount per expense, separated by “and” or a semicolon. Quantities and ambiguous numbers need manual review.')
        number=numbers[0];amount=float(number.group().replace(',',''))
        if amount<=0:raise ValueError('Expense amounts must be positive.')
        description=(chunk[:number.start()]+' '+chunk[number.end():]).strip()
        description=re.sub(r'\b(?:spent|paid|bought|PKR|Rs)\b\.?','',description,flags=re.I)
        description=re.sub(r'^\s*(?:on|for)\s+','',description,flags=re.I).strip(' .')
        if not description:raise ValueError('Describe what each amount was spent on.')
        prediction=classify(description) if classify else None
        rows.append({'date':day,'description':description,'amount':amount,'currency':currency,'category':prediction[0] if prediction else 'Other','model_confidence':float(prediction[1]) if prediction else None})
    return rows


def save_batch(workspace,rows,affects_cash=False,request_id=None):
    validated=[]
    for row in rows:
        day=pd.Timestamp(row['date']).date().isoformat()
        if day>cash_day():raise ValueError('Future purchases belong in planned carts or the simulator.')
        validated.append(validated_entry(workspace,day,row['amount'],'Expense',row['category'],row['description'],row.get('merchant',''),row.get('currency'),row.get('text','')))
    if not validated:raise ValueError('No expenses to save.')
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        token,encoded,old=replay(conn,workspace,'batch',{'rows':validated,'affects_cash':affects_cash},request_id)
        if old is not None:return 0
        for entry in validated:insert_entry(conn,workspace,entry,'natural language',affects_cash)
        receipt(conn,workspace,token,encoded,{'count':len(validated)})
    return len(validated)


def render_text_capture(workspace,today,classify):
    if workspace=='Household sample':return
    with st.expander('Add several expenses in one sentence',expanded=True):
        text=st.text_area('Tell us what you spent',placeholder='Spent 350 on biryani and 150 on rickshaw. Yesterday.',key='multi_expense_text')
        if st.button('Extract expenses'):
            try:
                st.session_state['capture_rows_'+workspace]=parse_expenses(text,today,classify)
                st.session_state['capture_revision']=st.session_state.get('capture_revision',0)+1
            except ValueError as error:st.error(str(error))
        rows=st.session_state.get('capture_rows_'+workspace)
        if rows:
            st.caption('Amounts and dates are parsed by rules; categories come from DistilBERT when available. Missing dates use today. Saved account corrections guide later suggestions; similarity scores are not calibrated probabilities. Edit every row before saving.')
            with st.form('capture_review_'+str(st.session_state.get('capture_revision',0))):
                edited=st.data_editor(pd.DataFrame(rows),hide_index=True,num_rows='dynamic',column_config={'category':st.column_config.SelectboxColumn(options=CATEGORIES),'date':st.column_config.DateColumn(max_value=today),'model_confidence':st.column_config.NumberColumn(disabled=True,format='%.2f')})
                affect=st.checkbox('Deduct these new expenses from my wallet',value=wallet(workspace) is not None)
                submitted=st.form_submit_button('Save reviewed expenses')
            if submitted:
                try:
                    count=save_batch(workspace,edited.to_dict('records'),affect)
                    st.session_state.pop('capture_rows_'+workspace,None)
                    st.success(f'Saved {count} expenses. Reopen Financial HQ to see your new balance.')
                    st.rerun()
                except (ValueError,TypeError) as error:st.error(str(error))
