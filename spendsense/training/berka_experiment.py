"""Shared experiment utilities. Estimators are trained from scratch, never pretrained."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression,Ridge,LogisticRegression
from sklearn.ensemble import GradientBoostingRegressor,GradientBoostingClassifier

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval'/'berka_modeling_v1'
CACHE=ROOT.parent/'work'/'berka_modeling_v1'
MODELS=ROOT/'models'/'berka_low_balance_v1'
PROTOCOL=ROOT/'app'/'data'/'low_balance_protocol_v1.json'
SEED=20261119
BINARY_FEATURES=['previous_close_lower_ratio','previous_close_upper_ratio','netflow_median_3m_ratio','outflow_lag1_ratio','credit_median_3m_ratio']
REG_FEATURES=BINARY_FEATURES+['netflow_lag1_ratio','outflow_lag2_ratio','outflow_lag3_ratio']


def stamp():return datetime.now(ZoneInfo('Asia/Karachi')).isoformat(timespec='seconds')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,indent=2,default=str,allow_nan=False),encoding='utf-8')


def verify_protocol():
    p=read(PROTOCOL);digest=read(ROOT/'eval'/'berka_low_balance'/'freeze_digest.json')
    assert sha(PROTOCOL)==digest['protocol_sha256']
    assert p['selected_event']=='B' and p['coverage_policy']=='relaxed'
    assert p['secondary_binary_event']['ratio_threshold']==.05
    assert sha(ROOT/p['cohort']['file'])==p['cohort']['sha256']
    assert sha(ROOT/p['split']['file'])==p['split']['sha256']
    return p


def preregister():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True);MODELS.mkdir(parents=True,exist_ok=True)
    plan=OUT/'training_authorization_and_plan.json'
    if plan.exists():return read(plan)
    verify_protocol()
    regression=[{'name':'linear','kind':'linear','params':{}},
        *[{'name':'ridge_'+str(alpha),'kind':'ridge','params':{'alpha':alpha}} for alpha in (.1,1,10,100,1000)],
        *[{'name':f'gb_d{depth}_lr{rate}_leaf{leaf}','kind':'gbr','params':{'n_estimators':100,'max_depth':depth,'learning_rate':rate,'min_samples_leaf':leaf,'random_state':SEED}}
          for depth,rate,leaf in ((1,.03,50),(1,.05,100),(2,.03,100),(2,.05,100))]]
    logistic=[{'name':'logistic_C'+str(c),'kind':'logistic','params':{'C':c,'solver':'lbfgs','max_iter':2000,'tol':1e-7,'random_state':SEED}}
              for c in (.001,.01,.1)]
    binary_boost={'name':'binary_gb_stump','kind':'gbc','params':{'n_estimators':50,'max_depth':1,'learning_rate':.03,'min_samples_leaf':100,'random_state':SEED}}
    value={'authorized_at':stamp(),'authorization':'User explicitly permitted training under frozen protocol; this supersedes the old no-training status without editing the frozen contract.',
        'protocol_sha256':sha(PROTOCOL),'seed':SEED,'regression_features':REG_FEATURES,'binary_features':BINARY_FEATURES,
        'development_scope':'Original train target periods <=1996 and original validation target periods in 1997, pooled only for grouped CV and final development refit. No test rows used.',
        'cv':'3 deterministic GroupKFold account groups x validation years 1995/1996/1997. Train only outside held-out accounts and with outcomes strictly earlier than the validation year. Nine possible grouped forward folds.',
        'regression_selection':'Within family minimize pooled OOF account-macro MAE. Overall development preference uses common-case OOF MAE across baselines/selected families. No test-based selection.',
        'binary_selection':'Heavily regularized logistic grid, choose minimum pooled OOF account-macro Brier; numerical ties <=1e-6 prefer smaller C. Fixed probability threshold .5. Never optimize the fixed 3-positive validation subset alone.',
        'binary_boost_gate':'Only retain fixed depth-1 candidate if grouped OOF account-macro Brier improves >=5% relative to selected logistic, paired 2000-account-bootstrap 95% Brier-difference interval is entirely <0, and account-weighted average precision does not decrease.',
        'fit_weights':'Each account equal total weight; row weights inverse account-month count, normalized to mean 1. StandardScaler fitted within each training fold with the same weights; no target/feature imputation or clipping.',
        'regression_candidates':regression,'logistic_candidates':logistic,'binary_boost_candidate':binary_boost,
        'bootstrap':{'draws':2000,'seed':SEED,'unit':'account cluster within partition','confidence':.95,'paired':True},
        'test':'One locked evaluation pass after configurations, features, model files and development-selected preference are hashed. Plot/metric regeneration reads saved predictions only; no repeat scoring.'}
    save(plan,value);save(OUT/'plan_digest.json',{'sha256':sha(plan)})
    return value


def weights(accounts):
    series=pd.Series(accounts).reset_index(drop=True)
    w=1/series.map(series.value_counts()).to_numpy(dtype=float)
    return w/w.mean()


def account_losses(accounts,truth,prediction,squared=False):
    error=np.asarray(prediction)-np.asarray(truth)
    values=error**2 if squared else np.abs(error)
    return pd.Series(values).groupby(np.asarray(accounts)).mean()


def reg_metrics(accounts,truth,prediction):
    return {'mae':float(account_losses(accounts,truth,prediction).mean()),'rmse':float(np.sqrt(account_losses(accounts,truth,prediction,True).mean()))}


def macro_brier(accounts,truth,probability):
    return float(pd.Series((np.asarray(probability)-np.asarray(truth))**2).groupby(np.asarray(accounts)).mean().mean())


def fit(spec,data,target,features):
    w=weights(data.account_id)
    scaler=StandardScaler().fit(data[features].to_numpy(),sample_weight=w)
    builders={'linear':LinearRegression,'ridge':Ridge,'gbr':GradientBoostingRegressor,'logistic':LogisticRegression,'gbc':GradientBoostingClassifier}
    model=builders[spec['kind']](**spec['params'])
    model.fit(scaler.transform(data[features].to_numpy()),data[target].to_numpy(),sample_weight=w)
    return {'spec':spec,'features':features,'scaler':scaler,'model':model,'train_accounts':sorted(data.account_id.unique().tolist()),'protocol_sha256':sha(PROTOCOL)}


def predict(bundle,data):
    x=bundle['scaler'].transform(data[bundle['features']].to_numpy())
    return bundle['model'].predict_proba(x)[:,1] if bundle['spec']['kind'] in ('logistic','gbc') else bundle['model'].predict(x)


def clustered_regression(frame,predictions):
    names=list(predictions);ids=np.sort(frame.account_id.unique());n=len(ids)
    absolute=np.column_stack([account_losses(frame.account_id,frame.month_end_ratio,predictions[name]).reindex(ids).to_numpy() for name in names])
    squared=np.column_stack([account_losses(frame.account_id,frame.month_end_ratio,predictions[name],True).reindex(ids).to_numpy() for name in names])
    draws=np.random.default_rng(SEED).multinomial(n,np.full(n,1/n),size=2000)
    maes=draws@absolute/n;rmses=np.sqrt(draws@squared/n)
    result={}
    for index,name in enumerate(names):
        result[name]={'accounts':n,'months':len(frame),'mae':float(absolute[:,index].mean()),'rmse':float(np.sqrt(squared[:,index].mean())),
            'mae_ci95':np.quantile(maes[:,index],[.025,.975]).tolist(),'rmse_ci95':np.quantile(rmses[:,index],[.025,.975]).tolist()}
    return result,maes,rmses,names
