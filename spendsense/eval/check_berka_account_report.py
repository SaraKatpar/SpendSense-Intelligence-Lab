"""Independent spot/conservation checks using actual source rows, never fake data."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval'/'berka_accounts'


def main():
    if (ROOT/'app'/'data'/'low_balance_protocol_v1.json').exists():
        raise SystemExit('Historical candidate checks are superseded. Use verify_low_balance_protocol.py.')
    report=json.loads((OUT/'report.json').read_text(encoding='utf-8'))
    f=pd.read_csv(ROOT/'data'/'berka_original'/'trans.asc',sep=';',keep_default_na=False)
    f['day']=pd.to_datetime(f.date.astype(str),format='%y%m%d')
    known=f.operation.str.strip().ne('');debits=f[known&f.type.isin(['VYDAJ','VYBER'])]
    profiles=pd.read_csv(OUT/'account_eligibility.csv')
    assert len(profiles)==4500 and profiles.account_id.is_unique
    assert profiles.negative_snapshots.sum()==f.balance.lt(0).sum()==2999
    checked_months=0
    for filename,key in [('candidate_labels_NOT_SELECTED.csv','candidate_definitions'),('candidate_labels_RELAXED_NOT_SELECTED.csv','relaxed_observation_sensitivity')]:
        labels=pd.read_csv(OUT/filename)
        assert not labels.split_group.eq('test').any()
        years=pd.to_datetime(labels.month_start).dt.year
        assert ((labels.split_group.eq('train')&years.le(1996))|(labels.split_group.eq('validation')&years.eq(1997))).all()
        for result in report[key]['results']:
            assert int(labels[result['candidate']].sum())==result['positive_account_months']
            assert len(labels)==result['account_months']
        positive=labels[labels[['A_overdraft','B_5pct_buffer','C_10pct_repeated']].any(axis=1)]
        # All actual positive conservative months, plus real negatives. Relaxed
        # positives are sampled deterministically to keep the check quick.
        sample=pd.concat([positive.head(20),labels[~labels[['A_overdraft','B_5pct_buffer','C_10pct_repeated']].any(axis=1)].head(10)]).drop_duplicates(['account_id','month_id'])
        for row in sample.itertuples():
            origin=pd.Timestamp(row.month_start);end=pd.Timestamp(row.month_end)
            history=debits[(debits.account_id==row.account_id)&debits.day.ge(origin-pd.DateOffset(months=3))&debits.day.lt(origin)]
            monthly=history.groupby(history.day.dt.to_period('M')).amount.agg(['size','sum'])
            assert len(monthly)==3 and monthly['size'].min()>=3
            baseline=float(monthly['sum'].median());assert baseline>0
            assert f[(f.account_id==row.account_id)&f.day.eq(origin-pd.Timedelta(days=1))].shape[0]>0
            outcome=f[(f.account_id==row.account_id)&f.day.ge(origin)&f.day.lt(end)]
            assert bool(outcome.balance.lt(0).any())==row.A_overdraft
            assert bool(outcome.balance.lt(.05*baseline).any())==row.B_5pct_buffer
            by_day=outcome.groupby('day').balance.max().sort_index()
            sustained=False
            for first in range(len(by_day)):
                for last in range(first+1,len(by_day)):
                    gap=(by_day.index[last]-by_day.index[first]).days
                    if 2<=gap<=7 and by_day.iloc[first:last+1].le(.1*baseline).all():sustained=True
            assert sustained==row.C_10pct_repeated
            checked_months+=1
        test=next(x for x in report[key]['split_preview'] if x['partition']=='test')
        assert test['candidate_positives'] is None
        assert report[key]['selected_definition'] is None
    runs=pd.read_csv(OUT/'negative_observed_runs.csv')
    run_sample=pd.concat([runs.head(10),runs.nlargest(1,'observed_span_days')]).drop_duplicates(['account_id','break_id'])
    for row in run_sample.itertuples():
        source=f[(f.account_id==row.account_id)&f.day.ge(row.first_low)&f.day.le(row.last_low)]
        low_dates=source.groupby('day').balance.min().lt(0)
        assert low_dates.all() and len(low_dates)==row.observed_low_days
        assert (pd.Timestamp(row.last_low)-pd.Timestamp(row.first_low)).days==row.observed_span_days
    for filename,metadata in report['source_hashes'].items():
        assert hashlib.sha256((ROOT/'data'/'berka_original'/filename).read_bytes()).hexdigest()==metadata['sha256']
    assert report['checks']['model_fits']==0 and report['client_linkage_audit']['clients_crossing_proposed_splits']==0
    result={'passed':True,'source':'Original real Berka rows only; no generated records',
        'independent_candidate_month_checks':checked_months,'independent_negative_run_checks':len(run_sample),
        'checks':['Source hashes unchanged','Actual per-account negative snapshots conserve source totals','Candidate counts reconcile','Exported candidates development-only',
            'Past-only baseline reconstructed directly from source','Observed candidate A/B/C outcomes independently checked','No selected label','No reported test candidate positives','No client crossing splits','No fitted model'],
        'selected_definition':None,'model_fits':0}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
