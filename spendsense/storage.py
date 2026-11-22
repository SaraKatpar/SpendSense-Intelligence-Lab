"""Local, isolated workspaces. Demo records never mix with personal records."""
from pathlib import Path
from datetime import date,datetime
from zoneinfo import ZoneInfo
import sqlite3
import os
from contextlib import contextmanager
import pandas as pd
from app.finance import money,enforce_currency,change_cash,replay,receipt

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('SPENDSENSE_DB', str(ROOT / 'data' / 'spendsense.db')))
CATEGORIES = ['Food', 'Groceries', 'Transport', 'Shopping', 'Bills', 'Health', 'Education', 'Entertainment', 'Other']

def cash_day():return datetime.now(ZoneInfo('Asia/Karachi')).date().isoformat()

@contextmanager
def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY, workspace TEXT NOT NULL, date TEXT NOT NULL,
        amount REAL NOT NULL CHECK(amount > 0), kind TEXT NOT NULL,
        category TEXT NOT NULL, description TEXT NOT NULL, merchant TEXT,
        source TEXT NOT NULL DEFAULT 'manual')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS budgets (
        workspace TEXT, month TEXT, category TEXT, amount REAL,
        PRIMARY KEY(workspace, month, category))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS wallets (
        workspace TEXT PRIMARY KEY, cash REAL NOT NULL, payday TEXT NOT NULL,
        buffer REAL NOT NULL, food_daily REAL NOT NULL, transport_daily REAL NOT NULL,
        complete_history INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS commitments (
        id INTEGER PRIMARY KEY, workspace TEXT, label TEXT, due TEXT, amount REAL,
        category TEXT, paid INTEGER NOT NULL DEFAULT 0)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS missions (
        workspace TEXT, week TEXT, category TEXT, cap REAL,
        PRIMARY KEY(workspace, week))''')
    columns={row[1] for row in conn.execute('PRAGMA table_info(transactions)')}
    if 'wallet_revision' not in columns:
        conn.execute('ALTER TABLE transactions ADD COLUMN wallet_revision INTEGER')
    if 'commitment_id' not in columns:
        conn.execute('ALTER TABLE transactions ADD COLUMN commitment_id INTEGER')
    if 'currency' not in columns:
        conn.execute("ALTER TABLE transactions ADD COLUMN currency TEXT NOT NULL DEFAULT 'PKR'")
        conn.execute("UPDATE transactions SET currency='INR' WHERE workspace='Household sample'")
    conn.execute('CREATE TABLE IF NOT EXISTS intake_receipts(workspace TEXT,token TEXT,payload TEXT,result TEXT,PRIMARY KEY(workspace,token))')
    wallet_columns={row[1] for row in conn.execute('PRAGMA table_info(wallets)')}
    if 'asof' not in wallet_columns:conn.execute("ALTER TABLE wallets ADD COLUMN asof TEXT")
    conn.commit()
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def validated_entry(workspace,day,amount,kind,category,description,merchant='',currency=None,text=''):
    currency=enforce_currency(workspace,currency,' '.join(map(str,[description,merchant,text])))
    amount=money(amount,True)
    if kind not in ('Expense', 'Income') or category not in CATEGORIES:
        raise ValueError('Invalid transaction type or category.')
    day = date.fromisoformat(str(day)).isoformat()
    if not str(description).strip():
        raise ValueError('Please include a description.')
    return {'date':day,'amount':amount,'kind':kind,'category':category,'description':str(description).strip(),'merchant':str(merchant).strip(),'currency':currency}


def insert_entry(conn,workspace,entry,source='manual',affects_cash=False,commitment_id=None):
    """All financial intake uses this validator, including reviewed AI/mobile writes."""
    entry=validated_entry(workspace,entry['date'],entry['amount'],entry['kind'],entry['category'],entry['description'],entry.get('merchant',''),entry.get('currency'),entry.get('text',''))
    current=conn.execute('SELECT revision FROM wallets WHERE workspace=?',(workspace,)).fetchone() if affects_cash else None
    cursor=conn.execute('INSERT INTO transactions(workspace,date,amount,kind,category,description,merchant,source,wallet_revision,commitment_id,currency) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
        (workspace,entry['date'],entry['amount'],entry['kind'],entry['category'],entry['description'],entry['merchant'],source,current[0] if current else None,commitment_id,entry['currency']))
    if current:change_cash(conn,workspace,entry['amount']*(1 if entry['kind']=='Income' else -1),cash_day())
    return cursor.lastrowid


def add(workspace, day, amount, kind, category, description, merchant='', source='manual',affects_cash=False,currency=None,request_id=None,text=''):
    entry=validated_entry(workspace,day,amount,kind,category,description,merchant,currency,text)
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        token,encoded,old=replay(conn,workspace,'entry',{'entry':entry,'affects_cash':affects_cash},request_id)
        if old is not None:return old['id']
        identifier=insert_entry(conn,workspace,entry,source,affects_cash)
        receipt(conn,workspace,token,encoded,{'id':identifier})
        return identifier

def read(workspace):
    with connect() as conn:
        frame = pd.read_sql_query('SELECT * FROM transactions WHERE workspace=? ORDER BY date,id', conn, params=(workspace,))
    frame['date'] = pd.to_datetime(frame['date'])
    return frame

def budgets(workspace, month):
    with connect() as conn:
        return dict(conn.execute('SELECT category,amount FROM budgets WHERE workspace=? AND month=?', (workspace,month)))

def set_budget(workspace, month, category, amount):
    amount=money(amount)
    if category not in CATEGORIES:
        raise ValueError('Budget must be a finite, non-negative amount in a supported category.')
    with connect() as conn:
        conn.execute('INSERT OR REPLACE INTO budgets VALUES(?,?,?,?)', (workspace,month,category,float(amount)))

def delete(workspace, transaction_id):
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT amount,kind,wallet_revision,commitment_id FROM transactions WHERE workspace=? AND id=?',(workspace,int(transaction_id))).fetchone()
        if row and row[2] is not None:
            change_cash(conn,workspace,row[0]*(1 if row[1]=='Expense' else -1),cash_day(),row[2])
        if row and row[3] is not None:conn.execute('UPDATE commitments SET paid=0 WHERE id=? AND workspace=?',(row[3],workspace))
        conn.execute('DELETE FROM transactions WHERE workspace=? AND id=?', (workspace,int(transaction_id)))

def wallet(workspace):
    with connect() as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute('SELECT * FROM wallets WHERE workspace=?',(workspace,)).fetchone()
        return dict(row) if row else None

def save_wallet(workspace,cash,payday,buffer,food_daily,transport_daily,complete_history=False,currency=None,request_id=None):
    currency=enforce_currency(workspace,currency)
    cash,buffer,food_daily,transport_daily=[money(v) for v in (cash,buffer,food_daily,transport_daily)]
    payday=date.fromisoformat(str(payday)).isoformat()
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        token,encoded,old=replay(conn,workspace,'wallet',{'cash':cash,'payday':payday,'buffer':buffer,'food_daily':food_daily,'transport_daily':transport_daily,'complete_history':bool(complete_history),'currency':currency,'asof':cash_day()},request_id)
        if old is not None:return
        conn.execute('''INSERT INTO wallets(workspace,cash,payday,buffer,food_daily,transport_daily,complete_history,asof)
            VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(workspace) DO UPDATE SET cash=excluded.cash,payday=excluded.payday,
            buffer=excluded.buffer,food_daily=excluded.food_daily,transport_daily=excluded.transport_daily,
            complete_history=excluded.complete_history,asof=excluded.asof,revision=wallets.revision+1''',
            (workspace,float(cash),payday,float(buffer),float(food_daily),float(transport_daily),int(complete_history),cash_day()))
        receipt(conn,workspace,token,encoded,{'saved':True})

def commitments(workspace):
    with connect() as conn:
        return pd.read_sql_query('SELECT * FROM commitments WHERE workspace=? ORDER BY due,id',conn,params=(workspace,))

def add_commitment(workspace,label,due,amount,category='Bills',currency=None,request_id=None):
    currency=enforce_currency(workspace,currency,text=label)
    amount=money(amount,True)
    if not label.strip() or category not in CATEGORIES:raise ValueError('Enter a name, valid category and positive amount.')
    due=date.fromisoformat(str(due)).isoformat()
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        token,encoded,old=replay(conn,workspace,'commitment',{'label':label.strip(),'due':due,'amount':amount,'category':category,'currency':currency},request_id)
        if old is not None:return old['id']
        cursor=conn.execute('INSERT INTO commitments(workspace,label,due,amount,category) VALUES(?,?,?,?,?)',(workspace,label.strip(),due,float(amount),category))
        receipt(conn,workspace,token,encoded,{'id':cursor.lastrowid})
        return cursor.lastrowid

def pay_commitment(workspace,identifier,day):
    """Record payment locally, atomically; this never transfers actual money."""
    day=date.fromisoformat(str(day)).isoformat()
    with connect() as conn:
        conn.row_factory=sqlite3.Row
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM commitments WHERE workspace=? AND id=? AND paid=0',(workspace,int(identifier))).fetchone()
        if not row:return False
        insert_entry(conn,workspace,{'date':day,'amount':row['amount'],'kind':'Expense','category':row['category'],'description':row['label']},'planned',True,row['id'])
        conn.execute('UPDATE commitments SET paid=1 WHERE id=?',(row['id'],))
        return True

def mission(workspace,week,category=None,cap=None):
    with connect() as conn:
        if category is not None:
            cap=money(cap,True)
            if category not in CATEGORIES:raise ValueError('Enter a positive spending cap.')
            conn.execute('INSERT OR REPLACE INTO missions VALUES(?,?,?,?)',(workspace,str(week),category,float(cap)))
        row=conn.execute('SELECT category,cap FROM missions WHERE workspace=? AND week=?',(workspace,str(week))).fetchone()
        return {'category':row[0],'cap':row[1]} if row else None

def import_csv(workspace, frame, request_id=None):
    """Validate the full batch before a single atomic write. Export files round-trip."""
    required={'date','amount','kind','category','description'}
    if not required.issubset(frame.columns):
        raise ValueError('CSV requires date, amount, kind, category and description columns.')
    records=[]
    for row in frame.fillna('').to_dict('records'):
        records.append(validated_entry(workspace,str(row['date'])[:10],row['amount'],row['kind'],row['category'],row['description'],row.get('merchant',''),row.get('currency')))
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        token,encoded,old=replay(conn,workspace,'csv',records,request_id)
        if old is not None:return 0
        for entry in records:insert_entry(conn,workspace,entry,'csv',False)
        receipt(conn,workspace,token,encoded,{'count':len(records)})
    return len(records)


def correct_category_in_connection(conn,workspace,identifier,category):
    from app.personalization import learn,initialize,normalize
    initialize(conn)
    if category not in CATEGORIES:raise ValueError('Choose a supported category.')
    row=conn.execute('SELECT description,category FROM transactions WHERE workspace=? AND id=?',(workspace,int(identifier))).fetchone()
    if not row:raise ValueError('Transaction not found in this account.')
    last=conn.execute('SELECT category FROM category_corrections WHERE workspace=? AND normalized=? ORDER BY id DESC LIMIT 1',(workspace,normalize(row[0]))).fetchone()
    if row[1]==category and last and last[0]==category:return False
    conn.execute('UPDATE transactions SET category=? WHERE workspace=? AND id=?',(category,workspace,int(identifier)))
    learn(conn,workspace,row[0],category,datetime.now(ZoneInfo('Asia/Karachi')).isoformat(),int(identifier))
    return True


def correct_category(workspace,identifier,category,request_id=None):
    with connect() as conn:
        from app.personalization import initialize
        initialize(conn)
        conn.execute('BEGIN IMMEDIATE')
        if request_id is None:
            generation=conn.execute('SELECT MAX(id) FROM category_corrections WHERE workspace=? AND transaction_id=?',(workspace,int(identifier))).fetchone()[0]
            request_id=f'correction:{identifier}:{category}:{generation}'
        token,encoded,old=replay(conn,workspace,'category-correction',{'id':int(identifier),'category':category},request_id)
        if old is not None:return False
        changed=correct_category_in_connection(conn,workspace,identifier,category)
        receipt(conn,workspace,token,encoded,{'changed':changed})
        return changed
