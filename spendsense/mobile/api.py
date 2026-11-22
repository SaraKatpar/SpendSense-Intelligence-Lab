"""Same-origin mobile API. Private accounts share the existing SQLite database.

No client-supplied workspace is accepted. Financial writes and replay receipts
commit together. Run from spendsense: python -m uvicorn mobile.api:app --port 8765
"""
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictFloat

import storage
from chat_actions import money, validate
from app.finance import enforce_currency,change_cash,currency_of

STATIC=Path(__file__).parent/'static'
SESSION_AGE=7*24*3600
COOKIE='spendsense_session'
AI_LOCK=threading.Lock()
MODEL_LOCK=threading.Lock()
app=FastAPI(title='SpendSense Mobile',docs_url=None,redoc_url=None,openapi_url=None)


def today():return date.fromisoformat(storage.cash_day())
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def clean_json(value):return json.loads(json.dumps(value,default=str,allow_nan=False))


def initialize(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS mobile_users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,salt TEXT NOT NULL,password TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS mobile_sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL,csrf TEXT NOT NULL,expires REAL NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS mobile_attempts(address TEXT,created REAL)')
    conn.execute('CREATE TABLE IF NOT EXISTS mobile_requests(workspace TEXT,token TEXT,payload TEXT,result TEXT,PRIMARY KEY(workspace,token))')
    conn.execute('CREATE TABLE IF NOT EXISTS mobile_proposals(id TEXT PRIMARY KEY,workspace TEXT,proposal TEXT,expires REAL)')
    conn.execute('CREATE TABLE IF NOT EXISTS mobile_messages(id INTEGER PRIMARY KEY,workspace TEXT,role TEXT,content TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS coach_rules(workspace TEXT,label TEXT,category TEXT,cap REAL,PRIMARY KEY(workspace,label))')
    conn.execute('CREATE TABLE IF NOT EXISTS shopping_carts(id INTEGER PRIMARY KEY,workspace TEXT,label TEXT,amount REAL)')


@app.middleware('http')
async def security(request,call_next):
    if request.url.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        expected=f'{request.url.scheme}://{request.headers.get("host","")}'
        if request.headers.get('x-requested-with')!='SpendSense' or (origin and origin!=expected):
            return JSONResponse({'detail':'Open SpendSense in its own app tab and try again.'},status_code=403)
    result=await call_next(request)
    result.headers['X-Content-Type-Options']='nosniff'
    result.headers['Referrer-Policy']='same-origin'
    result.headers['X-Frame-Options']='DENY'
    result.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    if request.url.path.startswith('/api/'):result.headers['Cache-Control']='no-store'
    return result


@app.exception_handler(ValueError)
async def invalid(request,error):return JSONResponse({'detail':str(error)},status_code=422)


def account(request:Request):
    token=request.cookies.get(COOKIE,'')
    if not token:raise HTTPException(401,'Please sign in.')
    with storage.connect() as conn:
        initialize(conn)
        row=conn.execute('SELECT u.id,u.email,u.name,s.csrf FROM mobile_sessions s JOIN mobile_users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(digest(token),time.time())).fetchone()
    if not row:raise HTTPException(401,'Your session expired. Please sign in again.')
    if request.method not in ('GET','HEAD') and not hmac.compare_digest(request.headers.get('x-csrf-token',''),row[3]):raise HTTPException(403,'Session verification failed. Reload and try again.')
    return {'id':row[0],'email':row[1],'name':row[2],'csrf':row[3],'workspace':'mobile:'+row[0]}


class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Credentials(Strict):
    email:str=Field(min_length=3,max_length=160)
    password:str=Field(min_length=10,max_length=128)
    name:str=Field(default='',max_length=60)


def password_hash(password,salt):return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()


def throttle(request):
    address=request.client.host if request.client else 'local'
    with storage.connect() as conn:
        initialize(conn)
        conn.execute('DELETE FROM mobile_attempts WHERE created<?',(time.time()-900,))
        count=conn.execute('SELECT COUNT(*) FROM mobile_attempts WHERE address=?',(address,)).fetchone()[0]
        if count>=15:raise HTTPException(429,'Too many sign-in attempts. Try again in 15 minutes.')
        conn.execute('INSERT INTO mobile_attempts VALUES(?,?)',(address,time.time()))


def session(response,user):
    token=secrets.token_urlsafe(40);csrf=secrets.token_urlsafe(24)
    with storage.connect() as conn:
        initialize(conn)
        conn.execute('DELETE FROM mobile_sessions WHERE expires<?',(time.time(),))
        conn.execute('INSERT INTO mobile_sessions VALUES(?,?,?,?)',(digest(token),user[0],csrf,time.time()+SESSION_AGE))
    response.set_cookie(COOKIE,token,max_age=SESSION_AGE,httponly=True,samesite='strict',secure=os.getenv('SPENDSENSE_HTTPS')=='1',path='/')
    return {'name':user[2],'email':user[1],'csrf':csrf}


@app.post('/api/auth/register')
def register(body:Credentials,request:Request,response:Response):
    throttle(request)
    email=body.email.strip().lower();name=body.name.strip()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or not name:raise ValueError('Enter your name and a valid email address.')
    identifier=uuid.uuid4().hex;salt=secrets.token_hex(16)
    hashed=password_hash(body.password,salt)
    try:
        with storage.connect() as conn:
            initialize(conn)
            conn.execute('INSERT INTO mobile_users VALUES(?,?,?,?,?)',(identifier,email,name,salt,hashed))
    except sqlite3.IntegrityError:raise HTTPException(409,'An account with that email already exists. Sign in instead.')
    return session(response,(identifier,email,name))


@app.post('/api/auth/login')
def login(body:Credentials,request:Request,response:Response):
    throttle(request)
    with storage.connect() as conn:
        initialize(conn)
        user=conn.execute('SELECT id,email,name,salt,password FROM mobile_users WHERE email=?',(body.email.strip().lower(),)).fetchone()
    salt=user[3] if user else '00'*16
    match=hmac.compare_digest(password_hash(body.password,salt),user[4] if user else '0'*128)
    if not user or not match:raise HTTPException(401,'Email or password is incorrect.')
    return session(response,user)


@app.get('/api/me')
def me(user=Depends(account)):return {k:user[k] for k in ('name','email','csrf')}


@app.post('/api/auth/logout')
def logout(request:Request,response:Response,user=Depends(account)):
    with storage.connect() as conn:conn.execute('DELETE FROM mobile_sessions WHERE token=?',(digest(request.cookies[COOKIE]),))
    response.delete_cookie(COOKIE,path='/');return {'ok':True}


def wallet_version(profile):return digest(json.dumps(profile,sort_keys=True)) if profile else None


@app.get('/api/dashboard')
def dashboard(user=Depends(account)):
    from campus import runway
    from coach import rules,assess
    from shopping import carts
    workspace=user['workspace'];profile=storage.wallet(workspace);frame=storage.read(workspace);dues=storage.commitments(workspace)
    state=None;notice=None
    if profile:
        try:
            state=runway(profile,frame,dues,today())
            state={k:state[k] for k in ('days','daily_cap','optional_cap','essential_shortfall','safe_purchase_max','reserved','end_balance','runout','method')}
        except ValueError as error:notice=str(error)
    recent=frame[frame.date.ge(str(today()-timedelta(days=6)))&frame.date.le(str(today()))&frame.kind.eq('Expense')]
    series=[{'date':str(day),'amount':StrictFloat(recent.loc[recent.date.eq(str(day)),'amount'].sum())} for day in [today()-timedelta(days=n) for n in range(6,-1,-1)]]
    limits=[]
    for rule in rules(workspace).to_dict('records'):
        result=assess(frame,rule,today())
        limits.append({**rule,'spent':result['spent'],'remaining':result['remaining'],'over':result['over'],'repeat_flags':len(result['breaches'])})
    transactions=frame.sort_values(['date','id'],ascending=False).head(80).copy()
    transactions['date']=transactions.date.dt.strftime('%Y-%m-%d')
    return clean_json({'today':str(today()),'wallet':profile,'wallet_version':wallet_version(profile),'runway':state,'notice':notice,
        'transactions':transactions.fillna('').to_dict('records'),'commitments':dues.to_dict('records'),'carts':carts(workspace).to_dict('records'),
        'limits':limits,'week':series,'week_total':StrictFloat(recent.amount.sum()),'categories':storage.CATEGORIES})


class Mutation(Strict):request_id:str=Field(min_length=16,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')


def mutate(user,body,operation):
    payload=body.model_dump();token=payload.pop('request_id');encoded=json.dumps(payload,sort_keys=True,default=str)
    with storage.connect() as conn:
        initialize(conn);conn.execute('BEGIN IMMEDIATE')
        old=conn.execute('SELECT payload,result FROM mobile_requests WHERE workspace=? AND token=?',(user['workspace'],token)).fetchone()
        if old:
            if old[0]!=encoded:raise HTTPException(409,'This request was already used. Refresh before saving again.')
            return json.loads(old[1])
        result=operation(conn,user['workspace'])
        conn.execute('INSERT INTO mobile_requests VALUES(?,?,?,?)',(user['workspace'],token,encoded,json.dumps(result)))
        return result


class WalletInput(Mutation):
    cash:StrictFloat;payday:date;buffer:StrictFloat;food_daily:StrictFloat;transport_daily:StrictFloat
    complete_history:bool=False
    version:str|None=None
    currency:str='PKR'


@app.put('/api/wallet')
def save_wallet(body:WalletInput,user=Depends(account)):
    enforce_currency(user['workspace'],body.currency)
    values=[money(v) for v in (body.cash,body.buffer,body.food_daily,body.transport_daily)]
    if not today()<body.payday<=today()+timedelta(days=365):raise ValueError('Next allowance must be within the next 365 days.')
    def save(conn,workspace):
        conn.row_factory=sqlite3.Row
        row=conn.execute('SELECT * FROM wallets WHERE workspace=?',(workspace,)).fetchone()
        if wallet_version(dict(row) if row else None)!=body.version:raise HTTPException(409,'Your wallet changed. Reload before updating it.')
        conn.execute('''INSERT INTO wallets(workspace,cash,payday,buffer,food_daily,transport_daily,complete_history,asof) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(workspace) DO UPDATE SET cash=excluded.cash,payday=excluded.payday,buffer=excluded.buffer,food_daily=excluded.food_daily,
            transport_daily=excluded.transport_daily,complete_history=excluded.complete_history,asof=excluded.asof,revision=wallets.revision+1''',
            (workspace,values[0],str(body.payday),*values[1:],int(body.complete_history),str(today())))
        return {'ok':True}
    return mutate(user,body,save)


class TransactionInput(Mutation):
    amount:StrictFloat;date:date;kind:str='Expense';category:str;description:str=Field(min_length=1,max_length=300)
    currency:str='PKR'


@app.post('/api/transactions')
def transaction(body:TransactionInput,user=Depends(account)):
    action=validate({k:v for k,v in {'type':'transaction',**body.model_dump(mode='json')}.items() if k!='request_id'},today())
    def save(conn,workspace):
        current=conn.execute('SELECT revision FROM wallets WHERE workspace=?',(workspace,)).fetchone()
        if not current:raise ValueError('Set up your wallet first.')
        identifier=storage.insert_entry(conn,workspace,action,'mobile',True)
        return {'ok':True,'id':identifier}
    return mutate(user,body,save)


class DeleteInput(Mutation):id:int
class CategoryInput(DeleteInput):category:str


@app.post('/api/transactions/category')
def category_correction(body:CategoryInput,user=Depends(account)):
    def save(conn,workspace):
        return {'ok':True,'changed':storage.correct_category_in_connection(conn,workspace,body.id,body.category)}
    return mutate(user,body,save)


@app.post('/api/transactions/delete')
def delete_transaction(body:DeleteInput,user=Depends(account)):
    def remove(conn,workspace):
        row=conn.execute('SELECT amount,kind,wallet_revision,commitment_id FROM transactions WHERE id=? AND workspace=?',(body.id,workspace)).fetchone()
        if not row:raise HTTPException(404,'Transaction not found.')
        if row[2] is not None:change_cash(conn,workspace,row[0]*(1 if row[1]=='Expense' else -1),today(),row[2])
        if row[3] is not None:conn.execute('UPDATE commitments SET paid=0 WHERE workspace=? AND id=?',(workspace,row[3]))
        conn.execute('DELETE FROM transactions WHERE id=? AND workspace=?',(body.id,workspace))
        return {'ok':True}
    return mutate(user,body,remove)


class LimitInput(Mutation):category:str;amount:StrictFloat;currency:str='PKR'


@app.post('/api/limits')
def limit(body:LimitInput,user=Depends(account)):
    enforce_currency(user['workspace'],body.currency)
    action=validate({'type':'weekly_limit','currency':'PKR','category':body.category,'amount':body.amount},today())
    def save(conn,workspace):
        conn.execute('INSERT OR REPLACE INTO coach_rules VALUES(?,?,?,?)',(workspace,action['category'],action['category'],action['amount']))
        return {'ok':True}
    return mutate(user,body,save)


class PlannedInput(Mutation):label:str=Field(min_length=1,max_length=100);amount:StrictFloat;currency:str='PKR'
class DueInput(PlannedInput):due:date;category:str='Bills'


@app.post('/api/carts')
def cart(body:PlannedInput,user=Depends(account)):
    enforce_currency(user['workspace'],body.currency,body.label)
    amount=money(body.amount,True)
    if body.currency!='PKR' or not body.label.strip():raise ValueError('Enter a named cart with a PKR amount.')
    def save(conn,workspace):
        cursor=conn.execute('INSERT INTO shopping_carts(workspace,label,amount) VALUES(?,?,?)',(workspace,body.label.strip(),amount))
        return {'ok':True,'id':cursor.lastrowid}
    return mutate(user,body,save)


@app.post('/api/commitments')
def commitment(body:DueInput,user=Depends(account)):
    enforce_currency(user['workspace'],body.currency,body.label)
    amount=money(body.amount,True)
    if body.currency!='PKR' or not body.label.strip() or body.category not in storage.CATEGORIES:raise ValueError('Check your due name, category and PKR amount.')
    if not today()<=body.due<=today()+timedelta(days=365):raise ValueError('Choose a due date within the next year.')
    def save(conn,workspace):
        cursor=conn.execute('INSERT INTO commitments(workspace,label,due,amount,category) VALUES(?,?,?,?,?)',(workspace,body.label.strip(),str(body.due),amount,body.category))
        return {'ok':True,'id':cursor.lastrowid}
    return mutate(user,body,save)


@app.post('/api/commitments/pay')
def pay(body:DeleteInput,user=Depends(account)):
    def save(conn,workspace):
        row=conn.execute('SELECT amount,category,label,paid FROM commitments WHERE id=? AND workspace=?',(body.id,workspace)).fetchone()
        wallet=conn.execute('SELECT revision FROM wallets WHERE workspace=?',(workspace,)).fetchone()
        if not row:raise HTTPException(404,'Payment not found.')
        if not wallet:raise ValueError('Set up your wallet first.')
        if row[3]:return {'ok':True}
        storage.insert_entry(conn,workspace,{'date':str(today()),'amount':row[0],'kind':'Expense','category':row[1],'description':row[2]},'planned',True,body.id)
        conn.execute('UPDATE commitments SET paid=1 WHERE id=? AND workspace=?',(body.id,workspace))
        return {'ok':True}
    return mutate(user,body,save)


class Scenario(Strict):purchase:StrictFloat=0;delay:int=Field(default=0,ge=0,le=60)


@app.post('/api/scenario')
def scenario(body:Scenario,user=Depends(account)):
    from campus import runway
    profile=storage.wallet(user['workspace'])
    if not profile:raise ValueError('Set up your wallet first.')
    price=money(body.purchase);profile['payday']=str(date.fromisoformat(profile['payday'])+timedelta(days=body.delay))
    if date.fromisoformat(profile['payday'])>today()+timedelta(days=425):raise ValueError('Choose a shorter allowance horizon.')
    result=runway(profile,storage.read(user['workspace']),storage.commitments(user['workspace']),today(),purchase=price)
    return clean_json({k:result[k] for k in ('affordable','essential_shortfall','safe_purchase_max','daily_cap','optional_cap','end_balance','runout')})


class TextInput(Strict):text:str=Field(min_length=1,max_length=6000)


_classifier=None
def classify_global(text):
    global _classifier
    from storage import ROOT
    path=ROOT/'models'/'research'/'categorizer'
    if not (path/'config.json').exists():return None
    # Explicit artifact path and a dedicated lock: never change ml.MODELS globally.
    with MODEL_LOCK:
        import torch
        from transformers import AutoTokenizer,AutoModelForSequenceClassification
        from nltk.tokenize import wordpunct_tokenize
        if _classifier is None:
            _classifier=(AutoTokenizer.from_pretrained(path,local_files_only=True),AutoModelForSequenceClassification.from_pretrained(path,local_files_only=True).eval())
        tokenizer,model=_classifier
        with torch.no_grad():
            probs=model(**tokenizer(' '.join(wordpunct_tokenize(text.lower())),return_tensors='pt',truncation=True,max_length=64)).logits.softmax(-1)[0]
        index=int(probs.argmax());return model.config.id2label[index],float(probs[index])


def classify(text,workspace=None):
    result=classify_global(text)
    if workspace:
        from app.personalization import predict
        return predict(workspace,text,result)
    return result


@app.post('/api/capture/text')
def capture_text(body:TextInput,user=Depends(account)):
    from capture import parse_expenses
    rows=parse_expenses(body.text,today(),lambda text:classify(text,user['workspace']),user['workspace'])
    return clean_json({'rows':rows,'review_required':True})


@app.post('/api/capture/order')
def capture_order(body:TextInput,user=Depends(account)):
    from shopping import order_fields
    result=order_fields(body.text);result['currency']=currency_of(body.text)
    return clean_json(result)


@app.post('/api/capture/image')
async def capture_image(request:Request,user=Depends(account)):
    from PIL import Image
    from receipt_ocr import scan
    from starlette.concurrency import run_in_threadpool
    if request.headers.get('content-type','').split(';')[0] not in ('image/jpeg','image/png','image/webp'):raise ValueError('Choose a JPEG, PNG or WebP image.')
    content=bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content)>8*1024*1024:raise HTTPException(413,'Choose an image smaller than 8 MB.')
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.width*image.height>12_000_000:raise ValueError('Choose an image smaller than 12 megapixels.')
            image.verify()
    except (OSError,Image.DecompressionBombError):raise ValueError('This image could not be read.')
    try:result=await run_in_threadpool(scan,bytes(content))
    except RuntimeError as error:raise HTTPException(503,str(error))
    result['currency']=currency_of(result['text'])
    return clean_json(result)


@app.get('/api/insights')
def insights(user=Depends(account)):
    frame=storage.read(user['workspace'])
    return clean_json({'style':None,'spending_mix_status':'Research-only spending-mix clusters are not deployed; no student identity is inferred.',
        'forecast':'No personal LSTM or autoencoder is assigned to this new student account. Daily limits use your entered costs; reference household models are not substituted.',
        'categorizer':'Local trained DistilBERT; predictions must be reviewed.'})


class ChatInput(Strict):text:str=Field(min_length=1,max_length=2000)
class ProposalInput(Strict):id:str=Field(min_length=32,max_length=32)


@app.get('/api/chat')
def messages(user=Depends(account)):
    with storage.connect() as conn:
        initialize(conn)
        rows=conn.execute('SELECT role,content FROM (SELECT * FROM mobile_messages WHERE workspace=? ORDER BY id DESC LIMIT 40) ORDER BY id',(user['workspace'],)).fetchall()
        proposals=conn.execute('SELECT id,proposal FROM mobile_proposals WHERE workspace=? AND expires>? ORDER BY rowid DESC LIMIT 1',(user['workspace'],time.time())).fetchall()
    return {'messages':[{'role':r[0],'content':r[1]} for r in rows],
            'proposal':preview(proposals[0][0],json.loads(proposals[0][1])) if proposals else None}


def preview(identifier,proposal):return {k:proposal[k] for k in ('action','previous','cash_before','cash_after','target_description') if k in proposal}|{'id':identifier}


@app.post('/api/chat')
def chat(body:ChatInput,user=Depends(account)):
    from ai_chat import propose_change,reply,context_for
    import requests
    if not AI_LOCK.acquire(blocking=False):raise HTTPException(429,'Your local AI is answering another message. Try again shortly.')
    try:
        prior=messages(user)['messages'];history=prior+[{'role':'user','content':body.text}]
        action=propose_change(body.text,today(),workspace=user['workspace']);proposal=None
        if action is not None:
            # Workspace comes exclusively from the authenticated server session.
            proposal=prepare_mobile(user['workspace'],action)
            identifier=uuid.uuid4().hex
            answer='I prepared an account change. Check the fields and wallet impact, then apply or cancel it.'
        else:answer=reply(history,context_for(storage.read(user['workspace']),user['workspace'],today()))
        with storage.connect() as conn:
            initialize(conn)
            conn.execute('DELETE FROM mobile_proposals WHERE workspace=?',(user['workspace'],))
            if proposal:conn.execute('INSERT INTO mobile_proposals VALUES(?,?,?,?)',(identifier,user['workspace'],json.dumps(proposal),time.time()+600))
            for item in ({'role':'user','content':body.text},{'role':'assistant','content':answer}):conn.execute('INSERT INTO mobile_messages(workspace,role,content) VALUES(?,?,?)',(user['workspace'],item['role'],item['content']))
        return {'answer':answer,'proposal':preview(identifier,proposal) if proposal else None}
    except (requests.RequestException,RuntimeError):raise HTTPException(503,'Local Llama is unavailable. Start Ollama on the server and try again. No change was saved.')
    finally:AI_LOCK.release()


def prepare_mobile(workspace,action):
    from chat_actions import prepare
    return prepare(workspace,action,today(),allow_mobile=True)


@app.post('/api/chat/apply')
def apply_chat(body:ProposalInput,user=Depends(account)):
    from chat_actions import apply
    with storage.connect() as conn:
        initialize(conn)
        row=conn.execute('SELECT proposal FROM mobile_proposals WHERE id=? AND workspace=? AND expires>?',(body.id,user['workspace'],time.time())).fetchone()
    if not row:raise HTTPException(404,'This preview expired. Ask for the change again.')
    changed=apply(json.loads(row[0]),user['workspace'],today(),allow_mobile=True)
    with storage.connect() as conn:
        conn.execute('DELETE FROM mobile_proposals WHERE id=? AND workspace=?',(body.id,user['workspace']))
        if changed:conn.execute('INSERT INTO mobile_messages(workspace,role,content) VALUES(?,?,?)',(user['workspace'],'assistant','Account change saved. Your dashboard is up to date.'))
    return {'ok':True,'changed':changed}


@app.post('/api/chat/cancel')
def cancel_chat(body:ProposalInput,user=Depends(account)):
    with storage.connect() as conn:conn.execute('DELETE FROM mobile_proposals WHERE id=? AND workspace=?',(body.id,user['workspace']))
    return {'ok':True}


@app.get('/api/export')
def export(user=Depends(account)):
    data=dashboard(user)
    return Response(json.dumps(data,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="spendsense-finances.json"'})


@app.get('/api/health')
def health():return {'ok':True,'database':'sqlite','timezone':'Asia/Karachi','version':'1.1.0'}


@app.get('/sw.js')
def service_worker():return FileResponse(STATIC/'sw.js',media_type='application/javascript',headers={'Service-Worker-Allowed':'/','Cache-Control':'no-cache'})


app.mount('/',StaticFiles(directory=STATIC,html=True),name='mobile')
