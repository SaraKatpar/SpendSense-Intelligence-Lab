"""Verify the frozen protocol on original rows, without model fitting or tuning."""
import hashlib
import itertools
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.data.low_balance_protocol import closing_balance,EVENT_RATIO
OUT=ROOT/'eval'/'berka_low_balance'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path=ROOT/'app'/'data'/'low_balance_protocol_v1.json'
    p=json.loads(path.read_text(encoding='utf-8'));digest=json.loads((OUT/'freeze_digest.json').read_text(encoding='utf-8'))
    assert sha(path)==digest['protocol_sha256']==sha(OUT/'protocol_v1.json')
    assert p['selected_event']=='B' and p['coverage_policy']=='relaxed'
    assert EVENT_RATIO==p['secondary_binary_event']['ratio_threshold']==.05
    assert p['coverage']['min_distinct_observed_dates']==2 and p['coverage']['max_gap_days'] is None
    assert p['model_fits']==0 and p['training_authorized'] is False
    assert sha(OUT/'cohort_832.csv')==p['cohort']['sha256']
    assert sha(ROOT/p['split']['file'])==p['split']['sha256']
    accounts=pd.read_csv(OUT/'cohort_832.csv');assert len(accounts)==832 and accounts.account_id.is_unique
    development=pd.read_csv(OUT/'development_targets.csv')
    assert development.partition.isin(['train','validation']).all()
    availability=pd.read_csv(OUT/'monthly_target_availability.csv')
    assert not any('ratio' in col or 'event' in col for col in availability.columns)
    for name,meta in p['source_hashes'].items():assert sha(ROOT/'data'/'berka_original'/name)==meta['sha256']
    f=pd.read_csv(ROOT/'data'/'berka_original'/'trans.asc',sep=';',keep_default_na=False)
    f=f[f.account_id.isin(set(accounts.account_id))].copy()
    f['day']=pd.to_datetime(f.date.astype(str),format='%y%m%d');f['month_id']=f.day.dt.year*12+f.day.dt.month-1
    known=f.operation.str.strip().ne('')
    debits=f[known&f.type.isin(['VYDAJ','VYBER'])]
    monthly=debits.groupby(['account_id','month_id']).amount.sum()
    index=availability[availability.partition_period].copy()
    index['month_end']=pd.to_datetime(index.month_end)
    base=[]
    for row in index.itertuples():
        values=[monthly.loc[(row.account_id,row.month_id-offset)] for offset in (1,2,3)]
        base.append(float(np.median(values)))
    index['scale']=base
    outcomes=f.merge(index[['account_id','month_id','partition','month_end','scale']],on=['account_id','month_id'])
    outcomes=outcomes[outcomes.day.lt(outcomes.month_end)]
    outcomes['A']=outcomes.balance.lt(0);outcomes['B']=outcomes.balance.lt(.05*outcomes.scale)
    events=outcomes.groupby(['account_id','month_id','partition'])[['A','B']].any().reset_index()
    for expected in p['pre_freeze_counts']:
        subset=events[events.partition.eq(expected['partition'])]
        for name in ('A','B'):
            assert int(subset[name].sum())==expected[name+'_positive_account_months']
            assert subset.loc[subset[name],'account_id'].nunique()==expected[name+'_positive_accounts']
    test=next(x for x in p['pre_freeze_counts'] if x['partition']=='test')
    assert test['B_positive_account_months']==7 and p['secondary_binary_event']['classifier_status']=='exploratory'
    # Independently enumerate compatible orderings of small REAL month-end
    # transaction groups, not generated data, to verify unique terminal targets.
    endings=f[f.day.dt.is_month_end & f.account_id.isin(set(accounts.loc[accounts.partition.isin(['train','validation']),'account_id']))]
    terminal_checks=0
    for _,group in endings.groupby(['account_id','month_id']):
        result=closing_balance(group)
        if result['status']!='unique_ledger_terminal' or len(group)>6:continue
        after=np.rint(group.balance.to_numpy()*100).astype('int64')
        before=after-np.rint(group.amount.to_numpy()*100).astype('int64')*np.where(group.type.eq('PRIJEM'),1,-1)
        edges=list(zip(before,after));terminals=set()
        for order in itertools.permutations(range(len(edges))):
            if all(edges[order[i]][1]==edges[order[i+1]][0] for i in range(len(order)-1)):
                terminals.add(int(edges[order[-1]][1]))
        assert terminals=={round(result['point_czk']*100)}
        terminal_checks+=1
        if terminal_checks==20:break
    assert terminal_checks==20
    registry=pd.read_csv(OUT/'cohort_target_availability.csv');assert len(registry)==832
    assert registry.exact_target_months_all_source.gt(0).all()
    q=json.loads((OUT/'target_availability.json').read_text(encoding='utf-8'))
    assert registry.assigned_period_exact_targets.gt(0).sum()==q['assigned_period_accounts_with_exact_targets']==639
    config=p['future_evaluation']['bootstrap']
    assert config['replicates']==2000 and config['seed']==20261119 and config['confidence']==.95
    result={'passed':True,'checks':['Frozen contract/cohort/split hashes','Original source hashes','Fixed B=5%, relaxed policy',
        'Independent real-source A/B counts for all three partitions','Only authorized aggregate test outcomes released',
        'Development target export contains no test rows','20 exact terminal balances checked by compatible real-transaction orderings',
        '832 accounts retained with explicit 639 assigned-period exact-target availability','Bootstrap plan fixed; no intervals computed without predictions'],
        'event_classifier_status':'exploratory','model_fits':0,'test_tuning':False,'protocol_sha256':digest['protocol_sha256']}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
