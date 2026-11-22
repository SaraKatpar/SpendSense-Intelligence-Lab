"""Build monthly, past-only feature/target tables under the unchanged freeze."""
import sys
import numpy as np
import pandas as pd
from berka_experiment import ROOT,OUT,CACHE,REG_FEATURES,preregister,verify_protocol,save,sha
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'eval'))
from app.data.low_balance_protocol import closing_balance
from berka_account_report import load


def main():
    preregister();p=verify_protocol()
    if (OUT/'configuration_lock.json').exists():raise SystemExit('Configurations already locked; do not rebuild the test input.')
    accounts=pd.read_csv(ROOT/p['cohort']['file'])
    frame,_=load();frame=frame[frame.account_id.isin(set(accounts.account_id))].copy()
    index=pd.read_csv(ROOT/'eval/berka_low_balance/monthly_target_availability.csv',parse_dates=['month_start','month_end'])
    key=['account_id','month_id']
    debit=frame[frame.eligible_debit].groupby(key).amount.sum().rename('outflow')
    frame['signed_czk']=frame.amount*np.where(frame.type.eq('PRIJEM'),1,-1)
    monthly=frame.groupby(key).signed_czk.sum().rename('net').to_frame().join(debit)
    credit=frame[frame.type.eq('PRIJEM')].groupby(key).amount.sum().rename('credit')
    monthly=monthly.join(credit);monthly['credit']=monthly.credit.fillna(0)
    for lag in (1,2,3):
        lookup=pd.MultiIndex.from_arrays([index.account_id,index.month_id-lag])
        for column in ('outflow','net','credit'):index[f'{column}_{lag}']=monthly[column].reindex(lookup).to_numpy()
    scale=index[[f'outflow_{lag}' for lag in (1,2,3)]].median(axis=1)
    assert index[[f'outflow_{lag}' for lag in (1,2,3)]].notna().all().all() and scale.gt(0).all()
    closings=[]
    for (account,month),group in frame[frame.day.dt.is_month_end].groupby(key):
        closings.append({'account_id':account,'month_id':month,**closing_balance(group)})
    closing=pd.DataFrame(closings).set_index(key)
    current=closing.reindex(pd.MultiIndex.from_frame(index[key]))
    previous=closing.reindex(pd.MultiIndex.from_arrays([index.account_id,index.month_id-1]))
    index['month_end_ratio']=current.point_czk.to_numpy()/scale
    index['previous_close_lower_ratio']=previous.lower_czk.to_numpy()/scale
    index['previous_close_upper_ratio']=previous.upper_czk.to_numpy()/scale
    index['persistence']=previous.point_czk.to_numpy()/scale
    index['netflow_median_3m_ratio']=index[[f'net_{lag}' for lag in (1,2,3)]].median(axis=1)/scale
    index['credit_median_3m_ratio']=index[[f'credit_{lag}' for lag in (1,2,3)]].median(axis=1)/scale
    for lag in (1,2,3):index[f'outflow_lag{lag}_ratio']=index[f'outflow_{lag}']/scale
    index['netflow_lag1_ratio']=index.net_1/scale
    index['pace']=index.persistence+index.netflow_median_3m_ratio
    assert np.isfinite(index[REG_FEATURES].to_numpy()).all()
    index['feature_latest_date']=index.month_start-pd.Timedelta(days=1)
    assert index.feature_latest_date.lt(index.month_start).all()
    label_source=frame.merge(index[key+['month_end']].assign(scale=scale),on=key,validate='many_to_one')
    label_source=label_source[label_source.day.lt(label_source.month_end)]
    label_source['event']=label_source.balance.lt(.05*label_source.scale)
    event=label_source.groupby(key).event.any()
    index['low_balance_event_B']=event.reindex(pd.MultiIndex.from_frame(index[key])).to_numpy().astype(bool)
    # Match original frozen development targets before any estimation occurs.
    frozen=pd.read_csv(ROOT/'eval/berka_low_balance/development_targets.csv')
    development=index[index.partition_period & index.partition.isin(['train','validation'])].copy()
    joined=development.merge(frozen[key+['month_end_ratio','low_balance_event_B']],on=key,suffixes=('','_frozen'),validate='one_to_one')
    assert np.allclose(joined.month_end_ratio,joined.month_end_ratio_frozen,equal_nan=True)
    assert joined.low_balance_event_B.eq(joined.low_balance_event_B_frozen).all()
    for counts in p['pre_freeze_counts']:
        subset=index[index.partition_period & index.partition.eq(counts['partition'])]
        assert int(subset.low_balance_event_B.sum())==counts['B_positive_account_months']
    # Only feature ratios, labels and metadata enter model files, never CZK.
    cols=key+['partition','month_start','month_end','feature_latest_date','partition_period','month_end_ratio','low_balance_event_B','persistence','pace',*REG_FEATURES]
    development[cols].to_csv(CACHE/'development.csv',index=False)
    test=index[index.partition_period & index.partition.eq('test')]
    test[cols].to_csv(CACHE/'sealed_test.csv',index=False)
    # Selection-bias diagnostics are observational summaries, not fitted inputs.
    profiles=pd.read_csv(ROOT/'eval/berka_accounts/account_eligibility.csv')
    bias=accounts.merge(profiles[['account_id','first','last','full_span_months','full_month_debit_mean','full_month_ledger_mean','active_debit_fraction','negative_snapshots','ledger_rows']],on='account_id',validate='one_to_one')
    avail=pd.read_csv(ROOT/'eval/berka_low_balance/cohort_target_availability.csv')
    bias=bias.merge(avail[['account_id','assigned_period_origin_months','assigned_period_exact_targets']],on='account_id',validate='one_to_one')
    bias['scorable']=bias.assigned_period_exact_targets.gt(0)
    bias['negative_snapshot_fraction']=bias.negative_snapshots/bias.ledger_rows
    bias['ever_negative']=bias.negative_snapshots.gt(0)
    ratios=index.groupby('account_id').month_end_ratio.median().rename('median_month_end_ratio_all_source')
    bias=bias.join(ratios,on='account_id')
    bias['unscorable_reason']=np.where(bias.scorable,'scorable',np.where(bias.assigned_period_origin_months.eq(0),'no_eligible_origin_in_assigned_period','all_assigned_targets_unresolved'))
    bias.to_csv(CACHE/'selection_bias.csv',index=False)
    index[key+['partition','month_start','partition_period','month_end_ratio']].to_csv(CACHE/'source_target_audit.csv',index=False)
    save(OUT/'dataset_manifest.json',{'protocol_sha256':sha(ROOT/'app/data/low_balance_protocol_v1.json'),
        'development_sha256':sha(CACHE/'development.csv'),'sealed_test_sha256':sha(CACHE/'sealed_test.csv'),
        'features':REG_FEATURES,'source_hashes':p['source_hashes'],'scorable_accounts':int(bias.scorable.sum()),'unscorable_accounts':int((~bias.scorable).sum()),
        'development_accounts':int(development.account_id.nunique()),'development_months':len(development),'test_input':'Sealed until configuration lock; no predictions or metrics computed in preparation.',
        'checks':['Original source hashes verified','Frozen development targets reproduced exactly','All predictors dimensionless and strictly past-only','All frozen B counts match','No target/feature imputation or clipping','No estimator fits in preparation']})
    print('Prepared development features and sealed test inputs. Scorable/unscorable:',int(bias.scorable.sum()),int((~bias.scorable).sum()),flush=True)


if __name__=='__main__':main()
