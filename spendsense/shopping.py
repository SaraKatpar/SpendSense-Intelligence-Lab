"""Local order-email and screenshot intake; carts never move cash."""
import re
from email import policy
from email.parser import BytesParser
import pandas as pd
import streamlit as st
from receipt_ocr import extract_fields,scan
from storage import connect
from app.finance import money,enforce_currency,replay,receipt


def email_text(content):
    message=BytesParser(policy=policy.default).parsebytes(content)
    body=message.get_body(preferencelist=('plain','html')) if message.is_multipart() else message
    text=body.get_content() if body else ''
    if body and body.get_content_type()=='text/html':
        from html import unescape
        text=unescape(re.sub('<[^>]+>',' ',text))
    return f"{message.get('From','')}\n{message.get('Subject','')}\n{text}"


def order_fields(text):
    details=extract_fields(text)
    candidates=[]
    for match in re.finditer(r'(?im)^\s*(?:order total|grand total|total paid|amount paid|total amount|total|amount due)\s*[:\-]?\s*(?:(?:PKR|Rs\.?|USD|INR|\$)\s*)?([\d,]+(?:\.\d{1,2})?)\s*$',text):
        candidates.append(float(match.group(1).replace(',','')))
    if candidates:details['amount']=candidates[-1]
    merchant=re.search(r'(?im)^(?:store|merchant|sold by)\s*:\s*(.+)$',text)
    if merchant:details['merchant']=merchant.group(1).strip()
    details['category']='Shopping'
    return details


def carts(workspace,label=None,amount=None,currency=None,request_id=None,text=''):
    if label is not None:
        currency=enforce_currency(workspace,currency,str(label)+' '+text)
        amount=money(amount,True)
        if not str(label).strip():raise ValueError('Enter a cart name.')
    with connect() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS shopping_carts(id INTEGER PRIMARY KEY,workspace TEXT,label TEXT,amount REAL)')
        if label is not None:
            conn.execute('BEGIN IMMEDIATE')
            token,encoded,old=replay(conn,workspace,'cart',{'label':label,'amount':amount,'currency':currency},request_id)
            if old is None:
                cursor=conn.execute('INSERT INTO shopping_carts(workspace,label,amount) VALUES(?,?,?)',(workspace,label,amount))
                receipt(conn,workspace,token,encoded,{'id':cursor.lastrowid})
        return pd.read_sql_query('SELECT id,label,amount FROM shopping_carts WHERE workspace=? ORDER BY id DESC',conn,params=(workspace,))


def render_shopping(workspace,today,entry_form):
    st.subheader('Online shopping, meet your wallet')
    st.write('Drop a cart or order screenshot, paste an order email, or upload its .eml file. Check the extracted details, then save once.')
    if workspace=='Household sample':
        st.info('Choose My finances to track online shopping.');return
    upload=st.file_uploader('Cart, order confirmation or email',type=['png','jpg','jpeg','eml'],key='shopping_upload')
    text=st.text_area('Or paste your order email',placeholder='Store: Daraz\nOrder total: PKR 2,450',key='shopping_email')
    if st.button('Read shopping details'):
        try:
            if upload:
                details=order_fields(email_text(upload.getvalue())) if upload.name.lower().endswith('.eml') else order_fields(scan(upload.getvalue())['text'])
            elif text.strip():details=order_fields(text)
            else:st.warning('Add an image or order email first.');return
            st.session_state['shopping_details']=details
            st.session_state['shopping_version']=st.session_state.get('shopping_version',0)+1
        except Exception as error:st.error(str(error))
    details=st.session_state.get('shopping_details')
    if details:
        try:enforce_currency(workspace,details.get('currency'),details.get('text',''))
        except ValueError as error:st.error(str(error));return
        with st.expander('Text read from your upload'):st.text(details['text'])
        st.caption('Review the final total including shipping and discounts. Currency symbols and dates may be ambiguous. Check History before saving an order already recorded from a receipt.')
        bought=st.checkbox('I have placed this order — record it as an expense',key='shopping_bought')
        if bought:
            entry_form('shopping'+str(st.session_state.get('shopping_version',0)),details,'online shopping')
        else:
            with st.form('save_cart'):
                label=st.text_input('Cart name',value=details.get('merchant') or 'My cart')
                amount=st.number_input('Cart total (PKR)',min_value=0.0,value=float(details['amount']))
                st.caption('Saved carts are wishlists. They do not change cash, expenses or reserved commitments.')
                if st.form_submit_button('Save planned cart'):
                    if label.strip() and amount>0:
                        carts(workspace,label.strip(),amount,details.get('currency'),text=details.get('text',''));st.success('Cart saved. Your cash is unchanged.')
                    else:st.error('Enter a cart name and a positive total.')
    saved=carts(workspace)
    if not saved.empty:
        st.markdown('**Your planned carts**')
        st.dataframe(saved[['label','amount']],hide_index=True)
        st.caption('When you actually order, upload the confirmation and tick “I have placed this order”.')
