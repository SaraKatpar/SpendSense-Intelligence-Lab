"""Validated, reviewed local chat changes. Model output is never executable code."""
import json
import uuid
import re
from datetime import date
from decimal import Decimal, InvalidOperation
import storage
from app.finance import money,change_cash,enforce_currency,minor_units


def validate(action,today):
    if not isinstance(action,dict):raise ValueError('Invalid change request.')
    kind=action.get('type')
    fields={'transaction':{'type','currency','date','amount','kind','category','description'},
            'wallet':{'type','currency','field','value'},
            'weekly_limit':{'type','currency','category','amount'},
            'category_correction':{'type','currency','transaction_id','category'}}
    if kind not in fields or set(action)!=fields[kind] or action.get('currency')!='PKR':
        raise ValueError('Only supported PKR account changes can be prepared.')
    result=dict(action)
    if kind=='transaction':
        enforce_currency('My finances',action.get('currency'),action.get('description',''))
        day=date.fromisoformat(str(action['date']))
        if day>today:raise ValueError('Future purchases belong in planning, not spending history.')
        if action['kind'] not in ('Expense','Income') or action['category'] not in storage.CATEGORIES:raise ValueError('Invalid transaction category or type.')
        if not isinstance(action['description'],str) or not 1<=len(action['description'].strip())<=300:raise ValueError('Include a short description.')
        result['date']=str(day);result['amount']=money(action['amount'],True)
    elif kind=='wallet':
        if action['field'] not in ('cash','buffer','food_daily','transport_daily','payday'):raise ValueError('Unsupported wallet field.')
        result['value']=str(date.fromisoformat(str(action['value']))) if action['field']=='payday' else money(action['value'])
        if action['field']=='payday' and date.fromisoformat(result['value'])<today:raise ValueError('Next allowance date must be today or later.')
    elif kind=='category_correction':
        if type(action['transaction_id']) is not int or action['transaction_id']<=0 or action['category'] not in storage.CATEGORIES:raise ValueError('Choose a transaction and supported category.')
    else:
        if action['category'] not in storage.CATEGORIES+['Eating out']:raise ValueError('Invalid weekly limit category.')
        result['amount']=money(action['amount'],True)
    return result


def snapshot(conn,workspace):
    return json.dumps({table:conn.execute('SELECT * FROM '+table+' WHERE workspace=? ORDER BY rowid',(workspace,)).fetchall()
                      for table in ('wallets','transactions','coach_rules','category_corrections')},sort_keys=True)


def tables(conn):
    from app.personalization import initialize
    initialize(conn)
    conn.execute('CREATE TABLE IF NOT EXISTS coach_rules(workspace TEXT,label TEXT,category TEXT,cap REAL,PRIMARY KEY(workspace,label))')
    conn.execute('CREATE TABLE IF NOT EXISTS chat_changes(token TEXT PRIMARY KEY,workspace TEXT,action TEXT)')


def allowed(workspace,allow_mobile):
    return workspace == 'My finances' or bool(allow_mobile and isinstance(workspace,str) and re.fullmatch(r'mobile:[0-9a-f]{32}',workspace))


def prepare(workspace,action,today,allow_mobile=False):
    if not allowed(workspace,allow_mobile):raise ValueError('This workspace is read-only.')
    action=validate(action,today)
    with storage.connect() as conn:
        tables(conn)
        profile=conn.execute('SELECT * FROM wallets WHERE workspace=?',(workspace,)).fetchone()
        if action['type'] in ('wallet','transaction') and not profile:raise ValueError('Set up your wallet in Settings first.')
        before=snapshot(conn,workspace)
        cash=conn.execute('SELECT cash FROM wallets WHERE workspace=?',(workspace,)).fetchone()
        previous=None;target_description=None
        if action['type']=='wallet':
            previous=conn.execute('SELECT '+action['field']+' FROM wallets WHERE workspace=?',(workspace,)).fetchone()[0]
        if action['type']=='weekly_limit':
            row=conn.execute('SELECT cap FROM coach_rules WHERE workspace=? AND label=?',(workspace,action['category'])).fetchone()
            previous=row[0] if row else None
        if action['type']=='category_correction':
            row=conn.execute('SELECT category,description FROM transactions WHERE workspace=? AND id=?',(workspace,action['transaction_id'])).fetchone()
            if not row:raise ValueError('Transaction not found in this account.')
            previous=row[0]
            target_description=row[1]
    cash_before=cash[0] if cash else None
    cash_after=cash_before
    if action['type']=='transaction':cash_after=(minor_units(cash_before,signed=True)+minor_units(action['amount'])*(1 if action['kind']=='Income' else -1))/100
    if action['type']=='wallet' and action['field']=='cash':cash_after=action['value']
    return {'token':uuid.uuid4().hex,'workspace':workspace,'action':action,'before':before,'previous':previous,'cash_before':cash_before,'cash_after':cash_after,'target_description':target_description}


def apply(proposal,workspace,today,allow_mobile=False):
    if proposal['workspace']!=workspace or not allowed(workspace,allow_mobile):raise ValueError('Workspace changed; prepare this again.')
    action=validate(proposal['action'],today)
    with storage.connect() as conn:
        tables(conn)
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM chat_changes WHERE token=?',(proposal['token'],)).fetchone():return False
        if snapshot(conn,workspace)!=proposal['before']:raise ValueError('Your finances changed. Cancel and request a fresh preview.')
        if action['type']=='transaction':
            storage.insert_entry(conn,workspace,action,'ai-reviewed',True)
        elif action['type']=='wallet':
            revision=',revision=revision+1' if action['field']=='cash' else ''
            conn.execute('UPDATE wallets SET '+action['field']+'=?'+revision+',asof=? WHERE workspace=?',(action['value'],str(today),workspace))
        elif action['type']=='category_correction':
            storage.correct_category_in_connection(conn,workspace,action['transaction_id'],action['category'])
        else:
            conn.execute('INSERT OR REPLACE INTO coach_rules VALUES(?,?,?,?)',(workspace,action['category'],action['category'],action['amount']))
        conn.execute('INSERT INTO chat_changes VALUES(?,?,?)',(proposal['token'],workspace,json.dumps(action)))
    return True
