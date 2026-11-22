"""Summarize already-exported Berka tables. Does not produce model inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd


def summary(frame,path,identifier):
    return {'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(frame),'columns':list(frame.columns),
        'dtypes':frame.dtypes.astype(str).to_dict(),'sql_null_counts':{k:int(v) for k,v in frame.isna().sum().items()},
        'empty_or_whitespace_strings':{c:int(frame[c].dropna().astype(str).str.strip().eq('').sum()) for c in frame.select_dtypes(include=['object','str']).columns},
        'duplicate_primary_ids':int(frame[identifier].duplicated().sum()),'duplicate_complete_rows':int(frame.duplicated().sum())}


def counts(series):return {str(k):int(v) for k,v in series.value_counts(dropna=False).items()}


def audit(folder,format='csv'):
    # Columns were discovered by DESCRIBE and inspected before writing this audit.
    extension='.asc' if format=='asc' else '.csv'
    frames={name:pd.read_csv(folder/(name+extension),sep=';' if format=='asc' else ',',keep_default_na=False,na_values=['\\N']) for name in ('account','order','trans')}
    result={'source':'Archived original Berka files' if format=='asc' else 'CTU Financial MariaDB export',
            'currency':'CZK (user confirmed; tables have no currency column)','preprocessing_performed':False,'tables':{}}
    for name,frame in frames.items():result['tables'][name]=summary(frame,folder/(name+extension),name+'_id')
    accounts=frames['account'];orders=frames['order'];trans=frames['trans']
    ids=set(accounts.account_id)
    result['relationships']={'account_ids':len(ids),'transaction_accounts':int(trans.account_id.nunique()),'standing_order_accounts':int(orders.account_id.nunique()),
        'orphan_transaction_rows':int((~trans.account_id.isin(ids)).sum()),'orphan_order_rows':int((~orders.account_id.isin(ids)).sum())}
    for name in ('account','trans'):
        dates=pd.to_datetime(frames[name]['date'].astype(str),format='%y%m%d' if format=='asc' else '%Y-%m-%d',errors='coerce')
        result['tables'][name]['date']={'invalid':int(dates.isna().sum()),'first':str(dates.min()),'last':str(dates.max()),'distinct_dates':int(dates.nunique())}
        if name=='trans':
            result['tables'][name]['weekend_rows']=int(dates.dt.dayofweek.ge(5).sum())
            result['tables'][name]['rows_per_account']=trans.groupby('account_id').size().describe().to_dict()
    for name in ('order','trans'):
        values=pd.to_numeric(frames[name]['amount'],errors='coerce')
        result['tables'][name]['amount']={'invalid':int(values.isna().sum()),'zero':int(values.eq(0).sum()),'negative':int(values.lt(0).sum()),
            'minimum':float(values.min()),'median':float(values.median()),'maximum':float(values.max()),'fractional_rows':int((values%1!=0).sum())}
    result['tables']['trans']['negative_balance_rows']=int(trans.balance.lt(0).sum())
    result['tables']['trans']['type_counts']=counts(trans.type)
    result['tables']['trans']['operation_counts']=counts(trans.operation)
    result['tables']['trans']['k_symbol_counts']=counts(trans.k_symbol)
    result['tables']['order']['k_symbol_counts']=counts(orders.k_symbol)
    result['tables']['account']['frequency_counts']=counts(accounts.frequency)
    unknown=trans.operation.fillna('').astype(str).str.strip().eq('')
    result['unknown_operation']={'rows':int(unknown.sum()),'label':'bank_generated/unknown_operation',
        'cross_tab':trans.loc[unknown].groupby(['k_symbol','type'],dropna=False).size().rename('rows').reset_index().to_dict('records'),
        'retain_raw_rows':True,'include_in_balance_and_cash_flow':True,'include_in_spending_anomaly_persona_features':False}
    result['limitations']=[
        'No food/retail merchant labels or text notes exist in these tables; do not invent food share.',
        'Standing orders are recurring payment references, not verified subscription labels, and contain no execution dates.',
        'Accounts are not necessarily distinct people and are not a verified student sample.',
        'The MariaDB trans amount/balance schema is integer-valued; compare it with original ASC precision before source selection.',
        'CZK source; only scale-free model features are allowed. Never pool raw units with household INR or the PKR wallet.',
        'Net-flow ratio is a possible savings proxy only; credits can include transfers, not just earnings.',
        'Household history has no user ID; it is not extra independent people for persona clustering.',
        'No independent anomaly labels exist; do not report fraud precision/recall or accuracy.',
        'Dates and primary keys need account/time-aware splitting before modeling; no splits are made by this audit.']
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,default=Path('data/berka_raw'))
    parser.add_argument('--output',type=Path,default=Path('eval/berka_audit.json'));parser.add_argument('--format',choices=['csv','asc'],default='csv');args=parser.parse_args()
    result=audit(args.folder,args.format);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8');print(json.dumps(result,indent=2,allow_nan=False))
