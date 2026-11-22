"""Real-data account/label feasibility audit. No model fitting or chosen label.

From spendsense: python eval/berka_account_report.py
Raw ASC files are read-only. Calendar slots count observed records; they do not
create transactions, zero-fill spending histories or forward-fill balances.
"""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.data.berka_policy import label_rows,UNKNOWN_ROLE

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval'/'berka_accounts'
SOURCE=ROOT/'data'/'berka_original'


def distribution(series):
    values=pd.Series(series).dropna()
    if values.empty:return {'n':0}
    return {'n':len(values),'min':float(values.min()),'p10':float(values.quantile(.1)),
            'median':float(values.median()),'p90':float(values.quantile(.9)),
            'p95':float(values.quantile(.95)),'max':float(values.max()),'mean':float(values.mean())}


def assignment(identifier):
    bucket=int(hashlib.sha256(('spendsense-berka-split-v1:'+str(identifier)).encode()).hexdigest(),16)%100
    return 'train' if bucket<70 else 'validation' if bucket<85 else 'test'


def load():
    proof=json.loads((SOURCE/'provenance.json').read_text(encoding='utf-8'))
    for name,meta in proof['files'].items():
        if hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('Source hash changed: '+name)
    frame=pd.read_csv(SOURCE/'trans.asc',sep=';',keep_default_na=False)
    frame['day']=pd.to_datetime(frame.date.astype(str),format='%y%m%d')
    frame['month_id']=frame.day.dt.year*12+frame.day.dt.month-1
    frame=label_rows(frame)
    frame['eligible']=frame.record_role.ne(UNKNOWN_ROLE)
    # Audit of observed outflow, NOT an approved discretionary-spending mapping.
    # Both debit codes occur with withdrawal operations; preserve the raw codes.
    frame['eligible_debit']=frame.eligible & frame.type.isin(['VYDAJ','VYBER'])
    return frame,proof


def calendar_panel(frame):
    bounds=frame.groupby('account_id').day.agg(first='min',last='max')
    ids=[];months=[]
    for identifier,row in bounds.iterrows():
        first=row['first'].year*12+row['first'].month-1;last=row['last'].year*12+row['last'].month-1
        periods=np.arange(first,last+1);ids.extend([identifier]*len(periods));months.extend(periods)
    panel=pd.DataFrame({'account_id':ids,'month_id':months})
    panel['month_start']=pd.to_datetime({'year':panel.month_id//12,'month':panel.month_id%12+1,'day':1})
    panel['month_end']=panel.month_start+pd.offsets.MonthEnd(0)
    panel=panel.merge(bounds,on='account_id',validate='many_to_one')
    panel['full_span']=(panel.month_start>=panel['first']) & (panel.month_end<=panel['last'])
    observed=frame.groupby(['account_id','month_id']).agg(ledger_rows=('trans_id','size'),ledger_days=('day','nunique'),first_observed=('day','min'),last_observed=('day','max'))
    eligible=frame[frame.eligible].groupby(['account_id','month_id']).size().rename('eligible_rows')
    debits=frame[frame.eligible_debit].groupby(['account_id','month_id']).agg(debit_rows=('trans_id','size'),observed_outflow_czk=('amount','sum'))
    panel=panel.merge(observed,on=['account_id','month_id'],how='left').merge(eligible,on=['account_id','month_id'],how='left').merge(debits,on=['account_id','month_id'],how='left')
    for col in ('ledger_rows','ledger_days','eligible_rows','debit_rows','observed_outflow_czk'):panel[col]=panel[col].fillna(0)
    panel['active_debit_month']=panel.debit_rows.gt(0)
    # Count observation gaps, without filling in an unobserved balance.
    days=frame[['account_id','month_id','day']].drop_duplicates().sort_values(['account_id','day'])
    days['internal_gap']=days.groupby(['account_id','month_id']).day.diff().dt.days
    gaps=days.groupby(['account_id','month_id']).internal_gap.max().rename('internal_gap')
    panel=panel.merge(gaps,on=['account_id','month_id'],how='left')
    panel['max_observation_gap_days']=pd.concat([panel.internal_gap.fillna(0),(panel.first_observed-panel.month_start).dt.days,
        (panel.month_end-panel.last_observed).dt.days],axis=1).max(axis=1)
    panel.loc[panel.ledger_rows.eq(0),'max_observation_gap_days']=panel.loc[panel.ledger_rows.eq(0),'month_end'].dt.days_in_month
    panel=panel.sort_values(['account_id','month_id']).reset_index(drop=True)
    group=panel.groupby('account_id',sort=False)
    panel['prior_full_months']=group.full_span.cumsum()-panel.full_span.astype(int)
    active_full=panel.full_span & panel.active_debit_month
    panel['prior_active_months']=active_full.groupby(panel.account_id).cumsum()-active_full.astype(int)
    full_debits=panel.debit_rows.where(panel.full_span,0)
    panel['prior_debit_rows']=full_debits.groupby(panel.account_id).cumsum()-full_debits
    panel['prior_mean_debits']=panel.prior_debit_rows/panel.prior_full_months.replace(0,np.nan)
    panel['prior_active_fraction']=panel.prior_active_months/panel.prior_full_months.replace(0,np.nan)
    panel['baseline_outflow_czk']=group.observed_outflow_czk.transform(lambda x:x.shift().rolling(3,min_periods=3).median())
    panel['prior_three_min_debits']=group.debit_rows.transform(lambda x:x.shift().rolling(3,min_periods=3).min())
    panel['prior_three_full']=group.full_span.transform(lambda x:x.shift().rolling(3,min_periods=3).sum()).eq(3)
    panel['prior_month_end_observed']=group.last_observed.shift(1).eq(group.month_end.shift(1))
    panel['baseline_available']=panel.prior_three_full & panel.prior_three_min_debits.ge(3) & panel.baseline_outflow_czk.gt(0) & panel.prior_month_end_observed
    panel['outcome_observed']=panel.full_span & panel.ledger_days.ge(4) & panel.max_observation_gap_days.le(10)
    for n in (6,12,18):
        panel['risk_ready_'+str(n)]=panel.prior_full_months.ge(n)&panel.prior_mean_debits.ge(4)&panel.prior_active_fraction.ge(.8)&panel.baseline_available
        panel['scoreable_'+str(n)]=panel['risk_ready_'+str(n)] & panel.outcome_observed
    return panel,bounds


def profiles(frame,panel,bounds):
    full=panel[panel.full_span]
    profile=bounds.copy();profile['observed_calendar_months']=frame.groupby('account_id').month_id.nunique()
    profile['calendar_month_span']=(profile['last'].dt.year-profile['first'].dt.year)*12+profile['last'].dt.month-profile['first'].dt.month+1
    profile['ledger_rows']=frame.groupby('account_id').size()
    profile['eligible_rows']=frame[frame.eligible].groupby('account_id').size()
    profile['eligible_debit_rows']=frame[frame.eligible_debit].groupby('account_id').size()
    profile['unknown_operation_rows']=frame[~frame.eligible].groupby('account_id').size()
    grouped=full.groupby('account_id')
    profile['full_span_months']=grouped.size()
    profile['full_month_ledger_mean']=grouped.ledger_rows.mean()
    profile['full_month_ledger_median']=grouped.ledger_rows.median()
    profile['full_month_ledger_min']=grouped.ledger_rows.min()
    profile['full_month_ledger_max']=grouped.ledger_rows.max()
    profile['full_month_debit_mean']=grouped.debit_rows.mean()
    profile['full_month_debit_median']=grouped.debit_rows.median()
    profile['full_month_debit_rows']=grouped.debit_rows.sum()
    profile['active_debit_fraction']=grouped.active_debit_month.mean()
    for n in (6,12,18):profile['scoreable_risk_months_'+str(n)]=panel.groupby('account_id')['scoreable_'+str(n)].sum()
    profile=profile.fillna(0);profile['split_group']=[assignment(x) for x in profile.index]
    before_eval=full[full.groupby('account_id').cumcount(ascending=False).ge(3)]
    for n in (6,12,24):
        window=before_eval.groupby('account_id').tail(n).groupby('account_id')
        mean=window.debit_rows.mean().reindex(profile.index,fill_value=0)
        fraction=window.active_debit_month.mean().reindex(profile.index,fill_value=0)
        profile[f'forecast_{n}m_history_mean_debits']=mean
        profile[f'forecast_{n}m_history_active_fraction']=fraction
        profile[f'forecast_{n}m_ready']=(profile.full_span_months.ge(n+3)&mean.ge(4)&fraction.ge(.8))
    for n,minimum in ((3,10),(6,20),(12,40)):
        window=full.groupby('account_id').tail(n).groupby('account_id')
        rows=window.debit_rows.sum().reindex(profile.index,fill_value=0)
        fraction=window.active_debit_month.mean().reindex(profile.index,fill_value=0)
        profile[f'persona_{n}m_debits']=rows
        profile[f'persona_{n}m_active_fraction']=fraction
        profile[f'persona_{n}m_ready']=profile.full_span_months.ge(n)&rows.ge(minimum)&fraction.ge(.8)
    for n in (6,12,18):profile[f'risk_{n}m_3_outcomes_ready']=profile[f'scoreable_risk_months_{n}'].ge(3)
    return profile


def eligibility(profile,panel):
    forecast=[];risk=[];personas=[]
    full=panel[panel.full_span].sort_values(['account_id','month_id'])
    # A source-feasibility backtest reserves the final three full months.
    # Its activity gate sees only the preceding history, not held-out outcomes.
    before_eval=full[full.groupby('account_id').cumcount(ascending=False).ge(3)]
    for n in (6,12,24):
        history=profile.full_span_months.ge(n+3)
        window=before_eval.groupby('account_id').tail(n).groupby('account_id')
        mean=window.debit_rows.mean().reindex(profile.index,fill_value=0)
        fraction=window.active_debit_month.mean().reindex(profile.index,fill_value=0)
        forecast.append({'history_months':n,'evaluation_months_reserved':3,'total_full_span_months':n+3,'history_only_accounts':int(history.sum()),
            'with_mean_4_debits_per_month':int((history&mean.ge(4)).sum()),
            'with_80pct_active_debit_months':int((history&mean.ge(4)&fraction.ge(.8)).sum()),'proposed_minimum':n==12})
    for n in (6,12,18):
        ready=profile['scoreable_risk_months_'+str(n)]
        risk.append({'prior_history_months':n,'min_mean_debits':4,'min_active_fraction':.8,'prior_baseline_months':3,
            'accounts_with_1_scoreable_target':int(ready.ge(1).sum()),'accounts_with_3_scoreable_targets':int(ready.ge(3).sum()),
            'accounts_with_6_scoreable_targets':int(ready.ge(6).sum()),'scoreable_account_months':int(ready.sum()),'proposed_minimum':n==12})
    for n,events in ((3,10),(6,20),(12,40)):
        window=full.groupby('account_id').tail(n).groupby('account_id')
        counts=window.debit_rows.sum().reindex(profile.index,fill_value=0)
        fraction=window.active_debit_month.mean().reindex(profile.index,fill_value=0)
        history=profile.full_span_months.ge(n);volume=history&counts.ge(events);coverage=volume&fraction.ge(.8)
        personas.append({'full_span_months':n,'min_debit_rows':events,'history_only_accounts':int(history.sum()),
            'volume_scope':'last N full months only','with_min_debit_rows':int(volume.sum()),'with_80pct_active_debit_months':int(coverage.sum()),'proposed_minimum':n==6})
    return {'forecast':forecast,'run_out_risk':risk,'personas':personas}


def daily_balances(frame,panel):
    daily=frame.groupby(['account_id','month_id','day']).agg(balance_min=('balance','min'),balance_max=('balance','max'),snapshots=('balance','size')).reset_index().sort_values(['account_id','day'])
    daily=daily.merge(panel[['account_id','month_id','month_start','month_end','baseline_available','baseline_outflow_czk','scoreable_12']],on=['account_id','month_id'],validate='many_to_one')
    daily['negative_any']=daily.balance_min.lt(0);daily['negative_all']=daily.balance_max.lt(0)
    daily['near_valid']=daily.baseline_available
    snapshots=frame.merge(panel[['account_id','month_id','baseline_available','baseline_outflow_czk']],on=['account_id','month_id'],validate='many_to_one')
    snapshots['near_snapshot']=snapshots.baseline_available & snapshots.balance.ge(0)&snapshots.balance.le(.05*snapshots.baseline_outflow_czk)
    near=snapshots.groupby(['account_id','day']).near_snapshot.any().rename('near_any')
    daily=daily.merge(near,on=['account_id','day'],validate='one_to_one')
    daily['near_all']=daily.near_valid&daily.balance_min.ge(0)&daily.balance_max.le(.05*daily.baseline_outflow_czk)
    return daily,snapshots


def episodes(daily,flag,all_flag,valid=None):
    data=daily.sort_values(['account_id','day']).copy()
    data['valid']=True if valid is None else data[valid]
    data['low']=data[flag]&data.valid
    data['next_day']=data.groupby('account_id').day.shift(-1)
    data['next_valid']=data.groupby('account_id').valid.shift(-1).fillna(False).astype(bool)
    data['previous_day']=data.groupby('account_id').day.shift(1)
    data['previous_valid']=data.groupby('account_id').valid.shift(1).fillna(False).astype(bool)
    data['break_id']=(~data.low).groupby(data.account_id).cumsum()
    data['mixed']=data.low & ~data[all_flag]
    low=data[data.low].copy()
    if low.empty:return pd.DataFrame()
    low['gap_between_low_observations']=low.groupby(['account_id','break_id']).day.diff().dt.days.fillna(0)
    groups=low.groupby(['account_id','break_id'])
    result=groups.agg(first_low=('day','min'),last_low=('day','max'),observed_low_days=('day','size'),mixed_status_days=('mixed','sum'),max_gap_between_low_dates=('gap_between_low_observations','max')).reset_index()
    first=groups.head(1).set_index(['account_id','break_id']);last=groups.tail(1).set_index(['account_id','break_id'])
    result=result.set_index(['account_id','break_id'])
    result['previous_observed_day']=first.previous_day;result['next_observed_day']=last.next_day
    result['left_censored']=~first.previous_valid.astype(bool);result['right_censored']=~last.next_valid.astype(bool)
    result['observed_span_days']=(result.last_low-result.first_low).dt.days
    result['last_low_to_next_observation_days']=(result.next_observed_day-result.last_low).dt.days
    return result.reset_index()


def dip_summary(frame,snapshots,daily,output):
    result={'scope':'Observed post-transaction snapshots and observed-day runs; no daily balance imputation or exact continuous-duration claim.'}
    negative=episodes(daily,'negative_any','negative_all');near=episodes(daily,'near_any','near_all','near_valid')
    negative.to_csv(output/'negative_observed_runs.csv',index=False);near.to_csv(output/'near_zero_observed_runs.csv',index=False)
    for name,mask,events,flag,all_flag in [('negative',frame.balance.lt(0),negative,'negative_any','negative_all'),
                                          ('near_zero',snapshots.near_snapshot,near,'near_any','near_all')]:
        source=frame if name=='negative' else snapshots
        counts=source.loc[mask].groupby('account_id').size()
        denominator=4500 if name=='negative' else int(snapshots.loc[snapshots.baseline_available,'account_id'].nunique())
        result[name]={'definition':'balance < 0' if name=='negative' else '0 <= balance <= 5% of median eligible-debit outflow in previous 3 full months; each prior month >=3 debit records',
            'account_denominator':denominator,'accounts_ever':int(source.loc[mask,'account_id'].nunique()),'snapshots':int(mask.sum()),
            'snapshot_denominator':len(frame) if name=='negative' else int(snapshots.baseline_available.sum()),
            'snapshots_per_affected_account':distribution(counts),
            'observed_low_dates':int(daily[flag].sum()),'all_snapshots_low_dates':int(daily[all_flag].sum()),
            'mixed_status_dates':int((daily[flag]&~daily[all_flag]).sum()),'observed_runs':len(events),
            'runs_per_affected_account':distribution(events.groupby('account_id').size()) if len(events) else {},
            'observed_run_span_days':distribution(events.observed_span_days) if len(events) else {},
            'observed_dates_per_run':distribution(events.observed_low_days) if len(events) else {},
            'single_observed_day_runs':int(events.observed_low_days.eq(1).sum()) if len(events) else 0,
            'runs_with_low_observation_gap_gt7_days':int(events.max_gap_between_low_dates.gt(7).sum()) if len(events) else 0,
            'max_gap_within_observed_run_days':distribution(events.max_gap_between_low_dates) if len(events) else {},
            'right_censored_runs':int(events.right_censored.sum()) if len(events) else 0,
            'left_censored_runs':int(events.left_censored.sum()) if len(events) else 0,
            'last_low_to_next_nonlow_observation_days':distribution(events.loc[~events.right_censored,'last_low_to_next_observation_days']) if len(events) else {}}
    result['exact_zero']={'accounts':int(frame.loc[frame.balance.eq(0),'account_id'].nunique()),'snapshots':int(frame.balance.eq(0).sum())}
    result['affected_account_overlap']={'negative_and_near_zero':len(set(frame.loc[frame.balance.lt(0),'account_id'])&set(snapshots.loc[snapshots.near_snapshot,'account_id']))}
    return result,{'negative':negative,'near_zero':near}


def candidate_labels(daily,panel,output,relaxed=False):
    # All definitions share prediction time, history criteria and denominators.
    groups=panel.account_id.map(assignment)
    years=panel.month_start.dt.year
    development=(groups.eq('train')&years.le(1996))|(groups.eq('validation')&years.eq(1997))
    observed=panel.full_span & panel.ledger_days.ge(2) if relaxed else panel.outcome_observed
    scoreable=panel.risk_ready_12 & observed
    pool=panel[scoreable&development].copy().set_index(['account_id','month_id'])
    future=daily[daily.day.lt(daily.month_end)].merge(pool.reset_index()[['account_id','month_id']],on=['account_id','month_id'],how='inner',validate='many_to_one').sort_values(['account_id','month_id','day'])
    future['A_overdraft']=future.balance_min.lt(0)
    future['B_5pct_buffer']=future.balance_min.lt(.05*future.baseline_outflow_czk)
    future['C_confirmed_low']=future.balance_max.le(.10*future.baseline_outflow_czk)
    keys=['account_id','month_id']
    labels=future.groupby(keys)[['A_overdraft','B_5pct_buffer']].any()
    # A run of all-low observed dates spans >=2 days, with no gap >7 days and
    # no intervening non-low observed date. No intervening balance is imputed.
    future['gap']=future.groupby(keys).day.diff().dt.days
    future['new_run']=(~future.C_confirmed_low)|future.gap.gt(7)|future.gap.isna()
    future['run']=future.groupby(keys).new_run.cumsum()
    runs=future[future.C_confirmed_low].groupby(keys+['run']).day.agg(['min','max','size'])
    runs['qualifies']=runs['size'].ge(2)&(runs['max']-runs['min']).dt.days.ge(2)
    sustained=runs.groupby(level=[0,1]).qualifies.any().rename('C_10pct_repeated')
    pool=pool.join(labels).join(sustained)
    names=['A_overdraft','B_5pct_buffer','C_10pct_repeated']
    assert pool[['A_overdraft','B_5pct_buffer']].notna().all().all()
    for name in names:pool[name]=pool[name].fillna(False).astype(bool)
    pool['split_group']=[assignment(x) for x in pool.index.get_level_values(0)]
    filename='candidate_labels_RELAXED_NOT_SELECTED.csv' if relaxed else 'candidate_labels_NOT_SELECTED.csv'
    pool.reset_index()[['account_id','month_id','month_start','month_end','split_group',*names]].to_csv(output/filename,index=False)
    results=[]
    for name in names:
        positive=pool[name]
        results.append({'candidate':name,'account_months':len(pool),'positive_account_months':int(positive.sum()),
            'positive_month_rate_pct':float(100*positive.mean()) if len(pool) else None,
            'accounts':int(pool.index.get_level_values(0).nunique()),'accounts_ever_positive':int(pool.loc[positive].index.get_level_values(0).nunique()),
            'positive_account_rate_pct':float(100*pool.loc[positive].index.get_level_values(0).nunique()/pool.index.get_level_values(0).nunique()) if len(pool) else None})
    split_preview=[]
    for group,year_condition in [('train',years.le(1996)),('validation',years.eq(1997)),('test',years.eq(1998))]:
        available=panel[scoreable & groups.eq(group)&year_condition]
        subset=pool[pool.split_group.eq(group)]
        split_preview.append({'partition':group,'candidate_account_months':len(available),'accounts_with_candidate_months':int(available.account_id.nunique()),
            'candidate_positives':None if group=='test' else {name:int(subset[name].sum()) for name in names}})
    return {'selected_definition':None,'prediction_origin':'First day of month at 00:00; feature rows strictly earlier; outcomes before last calendar day.',
        'reference':'Median observed eligible-debit outflow of previous 3 full months; each has >=3 debit rows; prior month-end snapshot is already observed; CZK cancels in ratios.',
        'risk_history':'At origin >=12 full prior months, mean >=4 eligible debits/month and >=80% prior full months active.',
        'outcome_ascertainment':('Relaxed sensitivity: target full-span month has >=2 observed dates; no gap cap. Unobserved lows can be missed.' if relaxed else 'Target month spans source coverage, has >=4 transaction dates and <=10-day maximum gap including month edges. Retrospective scoring availability only, never a predictor.'),
        'rate_scope':'Development only: train-group targets through 1996 and validation-group targets in 1997. Proposed 1998 test labels are not exported or reported.',
        'cohort_before_outcome_gate':int((panel.risk_ready_12 & panel.full_span & development).sum()),
        'excluded_for_outcome_observation':int(((panel.risk_ready_12 & panel.full_span & development)&~observed).sum()),
        'results':results,'split_preview':split_preview},pool


def code_tables(frame,output):
    eligible=frame[frame.eligible]
    cross=eligible.groupby(['type','k_symbol'],dropna=False).size().rename('rows').reset_index()
    cross['k_symbol_display']=cross.k_symbol.map(lambda x:'<empty>' if x=='' else '<whitespace>' if not x.strip() else x)
    cross.to_csv(output/'eligible_type_symbol_counts.csv',index=False)
    operations=eligible.groupby(['type','operation','k_symbol'],dropna=False).size().rename('rows').reset_index()
    operations.to_csv(output/'eligible_operation_symbol_counts.csv',index=False)
    return {'eligible_rows':len(eligible),'type_counts':eligible.type.value_counts().astype(int).to_dict(),
            'symbol_counts':[{ 'value':value,'display':'<empty>' if value=='' else '<whitespace>' if not value.strip() else value,'rows':int(n)} for value,n in eligible.k_symbol.value_counts().items()],
            'type_symbol_cross_tab':cross.to_dict('records')}


def split_plan(frame,panel,profile):
    assignments=pd.DataFrame({'account_id':profile.index,'partition':profile.split_group.to_numpy()})
    assignments.to_csv(OUT/'proposed_account_split.csv',index=False)
    result=[]
    for name in ('train','validation','test'):
        accounts=set(assignments.loc[assignments.partition.eq(name),'account_id'])
        cutoff=pd.Timestamp('1996-12-31' if name!='test' else '1997-12-31')
        past=frame[frame.account_id.isin(accounts)&frame.day.le(cutoff)]
        if past.empty:continue
        last=past.groupby('account_id').day.max()
        available=panel[panel.account_id.isin(accounts)].copy()
        available['asof_last']=available.account_id.map(last)
        available=available[available.full_span & available.month_end.le(available.asof_last)]
        n=available.groupby('account_id').size();avg=available.groupby('account_id').debit_rows.mean();active=available.groupby('account_id').active_debit_month.mean();debits=available.groupby('account_id').debit_rows.sum()
        forecast_window=available.groupby('account_id').tail(12).groupby('account_id')
        forecast=n.ge(12)&forecast_window.debit_rows.mean().ge(4)&forecast_window.active_debit_month.mean().ge(.8)
        persona_window=available.groupby('account_id').tail(6).groupby('account_id')
        persona=n.ge(6)&persona_window.debit_rows.sum().ge(20)&persona_window.active_debit_month.mean().ge(.8)
        result.append({'partition':name,'assigned_accounts':len(accounts),'history_cutoff':str(cutoff.date()),
            'accounts_with_past_observations':int(past.account_id.nunique()),'forecast_12_history_ready':int(forecast.sum()),'persona_6_history_ready':int(persona.sum())})
    return result


def check_client_linkage(profile,proof):
    # Same verified source, inspected header before implementation; audit only.
    # No client demographics or identifiers are used as model features.
    archive=ROOT.parent/'work'/'berka_source'/'data_berka.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=proof['archive_sha256']:raise ValueError('Archive changed')
    with zipfile.ZipFile(archive) as bundle:data=bundle.read('disp.asc')
    dispositions=pd.read_csv(io.BytesIO(data),sep=';',keep_default_na=False)
    if list(dispositions.columns)!=['disp_id','client_id','account_id','type']:raise ValueError('Inspect changed disposition schema first')
    n=dispositions.groupby('client_id').account_id.nunique()
    joined=dispositions.merge(profile[['split_group']],left_on='account_id',right_index=True,validate='many_to_one')
    across=joined.groupby('client_id').split_group.nunique()
    if across.gt(1).any():raise ValueError('Shared client crosses proposed splits. Assign connected account/client groups before modeling.')
    return {'source':'disp.asc read directly from the same verified original ZIP for split audit only','sha256':hashlib.sha256(data).hexdigest(),
        'columns':list(dispositions.columns),'rows':len(dispositions),'clients':int(dispositions.client_id.nunique()),
        'accounts':int(dispositions.account_id.nunique()),'clients_with_multiple_accounts':int(n.gt(1).sum()),'clients_crossing_proposed_splits':int(across.gt(1).sum())}


def main():
    if (ROOT/'app'/'data'/'low_balance_protocol_v1.json').exists():
        raise SystemExit('Historical proposal generator disabled after low-balance protocol freeze. Use eval/berka_low_balance and the frozen protocol.')
    OUT.mkdir(parents=True,exist_ok=True)
    frame,proof=load();print('Verified original rows:',len(frame),flush=True)
    panel,bounds=calendar_panel(frame);profile=profiles(frame,panel,bounds)
    profile.reset_index().to_csv(OUT/'account_eligibility.csv',index=False)
    # Counts, timing and source-observation diagnostics only, not model features.
    monthly_columns=['account_id','month_id','month_start','month_end','full_span','ledger_rows','ledger_days','eligible_rows','debit_rows','active_debit_month','max_observation_gap_days','prior_full_months','prior_month_end_observed','baseline_available','outcome_observed','scoreable_6','scoreable_12','scoreable_18']
    panel[monthly_columns].to_csv(OUT/'monthly_observation_coverage.csv',index=False)
    print('Built account/month observation audit',flush=True)
    daily,snapshots=daily_balances(frame,panel)
    dips,dip_runs=dip_summary(frame,snapshots,daily,OUT)
    for name,source,mask,day_flag in [('negative',frame,frame.balance.lt(0),'negative_any'),('near_zero',snapshots,snapshots.near_snapshot,'near_any')]:
        profile[name+'_snapshots']=source.loc[mask].groupby('account_id').size().reindex(profile.index,fill_value=0)
        profile[name+'_observed_days']=daily.loc[daily[day_flag]].groupby('account_id').size().reindex(profile.index,fill_value=0)
        profile[name+'_observed_runs']=dip_runs[name].groupby('account_id').size().reindex(profile.index,fill_value=0)
    profile.reset_index().to_csv(OUT/'account_eligibility.csv',index=False)
    labels,pool=candidate_labels(daily,panel,OUT)
    relaxed_labels,_=candidate_labels(daily,panel,OUT,relaxed=True)
    full=panel[panel.full_span]
    result={'stage':'Feasibility audit only; no model fitting, no selected run-out label','currency':'CZK; scale-free candidate thresholds only; no PKR wallet writes',
        'source_hashes':proof['files'],'accounts':len(profile),'dates':{'first':str(frame.day.min().date()),'last':str(frame.day.max().date())},
        'history':{'calendar_span_months':distribution(profile.calendar_month_span),'full_span_months':distribution(profile.full_span_months),
            'account_mean_ledger_rows_per_full_month':distribution(profile.full_month_ledger_mean),
            'account_mean_eligible_debit_rows_per_full_month':distribution(profile.full_month_debit_mean),
            'all_account_month_ledger_rows':distribution(full.ledger_rows),'all_account_month_debit_rows':distribution(full.debit_rows),
            'full_span_account_months':len(full),'no_observed_debits_full_months':int(full.debit_rows.eq(0).sum())},
        'eligibility_proposals':eligibility(profile,panel),'balance_dips':dips,'eligible_codes':code_tables(frame,OUT),
        'candidate_definitions':labels,'relaxed_observation_sensitivity':relaxed_labels,'split_history_readiness':split_plan(frame,panel,profile),'client_linkage_audit':check_client_linkage(profile,proof),
        'within_day_ordering':{'total_account_dates':len(daily),'multiple_transaction_dates':int(daily.snapshots.gt(1).sum()),
            'method':'Use all daily min/max snapshots; never infer end-of-day order from trans_id or file order.'},
        'limitations':['Account history is observed-span coverage, not proof of a complete personal budget.',
            'Cash withdrawals/transfers are bank outflows, not verified consumption or discretionary spending.',
            'Observed low-run spans are not exact continuous dip duration; gaps and mixed-status days are reported.',
            'Only post-transaction account snapshots exist: no allowance, due-date, payday, cash-on-hand, other-account or subjective financial-distress truth.',
            'Global label rates are a requested descriptive audit, not a basis for tuning thresholds to the future test set.',
            'No risk label selected and no model trained.']}
    # Direct conservation/no-selection checks on real source records.
    assert len(frame)==1056320 and frame.eligible.sum()==873206 and len(profile)==4500
    assert result['candidate_definitions']['selected_definition'] is None
    assert sum(result['eligible_codes']['type_counts'].values())==873206
    assert not any(pd.isna(v) for v in profile.full_span_months)
    assert (panel.loc[panel.scoreable_12,'prior_full_months']>=12).all()
    assert (panel.loc[panel.baseline_available,'prior_three_min_debits']>=3).all()
    assert panel.loc[panel.baseline_available,'prior_month_end_observed'].all()
    for name in ('negative','near_zero'):
        assert 0<=dips[name]['right_censored_runs']<=dips[name]['observed_runs']
        assert 0<=dips[name]['left_censored_runs']<=dips[name]['observed_runs']
    assert pool[['A_overdraft','B_5pct_buffer','C_10pct_repeated']].sum().le(len(pool)).all()
    assert not (pool.split_group.eq('test')).any()
    assert (pool.A_overdraft<=pool.B_5pct_buffer).all()
    for proposal in result['eligibility_proposals']['forecast']:
        assert int(profile[f"forecast_{proposal['history_months']}m_ready"].sum())==proposal['with_80pct_active_debit_months']
    for proposal in result['eligibility_proposals']['personas']:
        assert int(profile[f"persona_{proposal['full_span_months']}m_ready"].sum())==proposal['with_80pct_active_debit_months']
    account_sets=[set(profile.index[profile.split_group.eq(x)]) for x in ('train','validation','test')]
    assert not(account_sets[0]&account_sets[1] or account_sets[0]&account_sets[2] or account_sets[1]&account_sets[2])
    for filename,meta in proof['files'].items():assert hashlib.sha256((SOURCE/filename).read_bytes()).hexdigest()==meta['sha256']
    result['checks']={'real_source_integrity':True,'row_conservation':True,'disjoint_proposed_accounts':True,'past_only_baseline':True,'selected_label':None,'model_fits':0}
    (OUT/'report.json').write_text(json.dumps(result,indent=2,default=str,allow_nan=False),encoding='utf-8')
    print(json.dumps({'eligibility':result['eligibility_proposals'],'dips':dips,'candidates':labels,'split':result['split_history_readiness']},indent=2,default=str),flush=True)


if __name__=='__main__':main()
