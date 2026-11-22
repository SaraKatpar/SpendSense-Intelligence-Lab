"""Count and freeze the user-selected monthly low-balance protocol; no training.

The 832 account IDs come from the already reviewed eligibility artifact.
Only aggregate A/B test counts are released. Test target values stay unexported.
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'eval'))
from app.data.low_balance_protocol import closing_balance,EVENT_RATIO,PARTITIONS
from berka_account_report import load,calendar_panel,assignment

OUT=ROOT/'eval'/'berka_low_balance'
FREEZE=ROOT/'app'/'data'/'low_balance_protocol_v1.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    if FREEZE.exists():raise SystemExit('Protocol v1 is already frozen. Do not overwrite; make an explicit documented amendment.')
    old_profile=ROOT/'eval'/'berka_accounts'/'account_eligibility.csv'
    prior=pd.read_csv(old_profile)
    accounts=prior.loc[prior.risk_12m_3_outcomes_ready,['account_id']].sort_values('account_id').reset_index(drop=True)
    assert len(accounts)==832 and accounts.account_id.is_unique
    accounts['partition']=accounts.account_id.map(assignment)
    accounts.to_csv(OUT/'cohort_832.csv',index=False)
    frame,source=load();panel,_=calendar_panel(frame)
    panel=panel[panel.account_id.isin(set(accounts.account_id))].copy()
    frame=frame[frame.account_id.isin(set(accounts.account_id))].copy()
    panel['partition']=panel.account_id.map(assignment)
    panel['relaxed_coverage']=panel.full_span & panel.ledger_days.ge(2)
    panel['origin_eligible']=panel.risk_ready_12 & panel.relaxed_coverage
    year=panel.month_start.dt.year
    panel['partition_period']=(panel.partition.eq('train')&year.le(1996))|(panel.partition.eq('validation')&year.eq(1997))|(panel.partition.eq('test')&year.eq(1998))
    origins=panel[panel.origin_eligible].copy()
    key=['account_id','month_id']
    before_end=frame.merge(origins[key+['month_end','baseline_outflow_czk']],on=key,how='inner')
    before_end=before_end[before_end.day.lt(before_end.month_end)]
    before_end['A']=before_end.balance.lt(0)
    before_end['B']=before_end.balance.lt(EVENT_RATIO*before_end.baseline_outflow_czk)
    events=before_end.groupby(key)[['A','B']].any()
    origins=origins.set_index(key).join(events)
    assert origins[['A','B']].notna().all().all()
    assigned=origins[origins.partition_period]
    counts=[]
    for part in PARTITIONS:
        selected=assigned[assigned.partition.eq(part)]
        counts.append({'partition':part,
            'A_positive_account_months':int(selected.A.sum()),'A_positive_accounts':int(selected.loc[selected.A].index.get_level_values(0).nunique()),
            'B_positive_account_months':int(selected.B.sum()),'B_positive_accounts':int(selected.loc[selected.B].index.get_level_values(0).nunique())})
    (OUT/'pre_freeze_AB_counts.json').write_text(json.dumps({'scope':'Fixed 832-account cohort; relaxed coverage; unchanged assignment/time split; counts only, no performance metrics',
        'counts':counts,'test_usage':'Only the user-authorized positive-count feasibility check; no tuning'},indent=2),encoding='utf-8')
    print('PRE-FREEZE A/B COUNTS',json.dumps(counts),flush=True)

    # Resolve month-end closing measurements using all ledger rows, including
    # bank-generated credits. No snapshot order is guessed and none is imputed.
    endings=frame.merge(panel[key+['month_end']],on=key,validate='many_to_one')
    endings=endings[endings.day.eq(endings.month_end)]
    measurements=[]
    for (account,month),group in endings.groupby(key):
        measurements.append({'account_id':account,'month_id':month,**closing_balance(group)})
    closing=pd.DataFrame(measurements)
    print('Month-end measurement statuses',closing.status.value_counts().to_dict(),flush=True)
    origins=origins.reset_index().merge(closing,on=key,how='left',validate='one_to_one')
    origins['status']=origins.status.fillna('no_month_end_observation')
    origins['month_end_ratio']=origins.point_czk/origins.baseline_outflow_czk
    origins['month_end_ratio_lower']=origins.lower_czk/origins.baseline_outflow_czk
    origins['month_end_ratio_upper']=origins.upper_czk/origins.baseline_outflow_czk
    previous=closing[key+['point_czk']].copy();previous.month_id+=1
    previous=previous.rename(columns={'point_czk':'previous_close_czk'})
    origins=origins.merge(previous,on=key,how='left',validate='one_to_one')
    origins['last_month_ratio_baseline']=origins.previous_close_czk/origins.baseline_outflow_czk
    # A monthly pace-rule specification, computed only from already observed
    # months. It is a deterministic target-scale diagnostic, not a fitted model.
    flows=frame.copy();flows['signed_czk']=flows.amount*np.where(flows.type.eq('PRIJEM'),1,-1)
    net=flows.groupby(key).signed_czk.sum().rename('net_flow_czk')
    history=panel.set_index(key).join(net).reset_index().sort_values(key)
    history['past_three_net_czk']=history.groupby('account_id').net_flow_czk.transform(lambda x:x.shift().rolling(3,min_periods=3).median())
    origins=origins.merge(history[key+['past_three_net_czk']],on=key,validate='one_to_one')
    origins['pace_rule_ratio']=(origins.previous_close_czk+origins.past_three_net_czk)/origins.baseline_outflow_czk
    origins['exact_target']=origins.month_end_ratio.notna()
    origins['baseline_inputs_available']=origins.last_month_ratio_baseline.notna()&origins.pace_rule_ratio.notna()
    registry=accounts.copy().set_index('account_id')
    for field,mask in [('origin_months_all_source',pd.Series(True,index=origins.index)),
                       ('exact_target_months_all_source',origins.exact_target),
                       ('assigned_period_origin_months',origins.partition_period),
                       ('assigned_period_exact_targets',origins.partition_period&origins.exact_target),
                       ('assigned_period_common_baseline_targets',origins.partition_period&origins.exact_target&origins.baseline_inputs_available)]:
        registry[field]=origins.loc[mask].groupby('account_id').size().reindex(registry.index,fill_value=0)
    registry.reset_index().to_csv(OUT/'cohort_target_availability.csv',index=False)
    # Index/status for all accounts has no test outcomes/ratios. Only development
    # targets are persisted; authorized test output is the aggregate count table.
    origins[key+['partition','month_start','month_end','partition_period','status','exact_target','baseline_inputs_available']].to_csv(OUT/'monthly_target_availability.csv',index=False)
    development=origins[origins.partition_period&origins.partition.isin(['train','validation'])].copy()
    development=development.rename(columns={'A':'audit_A_overdraft','B':'low_balance_event_B'})
    development[key+['partition','month_start','month_end','status','month_end_ratio','month_end_ratio_lower','month_end_ratio_upper',
        'last_month_ratio_baseline','pace_rule_ratio','audit_A_overdraft','low_balance_event_B']].to_csv(OUT/'development_targets.csv',index=False)
    availability=[]
    for part in PARTITIONS:
        rows=origins[origins.partition_period&origins.partition.eq(part)]
        availability.append({'partition':part,'registered_accounts':int(accounts.partition.eq(part).sum()),'origin_months':len(rows),
            'accounts_with_origins':int(rows.account_id.nunique()),'exact_target_months':int(rows.exact_target.sum()),
            'accounts_with_exact_targets':int(rows.loc[rows.exact_target,'account_id'].nunique()),
            'common_baseline_target_months':int((rows.exact_target&rows.baseline_inputs_available).sum()),
            'accounts_with_common_baseline_targets':int(rows.loc[rows.exact_target&rows.baseline_inputs_available,'account_id'].nunique())})
    quality={'cohort_accounts':832,'all_source_accounts_with_exact_target':int(origins.loc[origins.exact_target,'account_id'].nunique()),
        'all_source_origin_months':len(origins),'all_source_exact_target_months':int(origins.exact_target.sum()),
        'month_end_measurement_statuses_all_source':closing.status.value_counts().astype(int).to_dict(),
        'assigned_period_accounts_with_exact_targets':int(origins.loc[origins.partition_period&origins.exact_target,'account_id'].nunique()),
        'by_partition':availability,'limitation':'Registry retains all 832 accounts. Unresolved/missing exact targets and out-of-period accounts are marked unavailable, never zero-filled or silently scored.'}
    (OUT/'target_availability.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    test=next(x for x in counts if x['partition']=='test')
    exploratory=test['B_positive_account_months']<20
    stamp=datetime.now(ZoneInfo('Asia/Karachi')).isoformat(timespec='seconds')
    protocol={'version':'low_balance_v1','frozen_at':stamp,'timezone':'Asia/Karachi','name':'low-balance event',
        'selected_event':'B','audit_reference_only':'A; no model target selection or tuning on A','coverage_policy':'relaxed',
        'cohort':{'accounts':832,'file':'eval/berka_low_balance/cohort_832.csv','sha256':sha(OUT/'cohort_832.csv'),
            'provenance':'Explicit fixed IDs from reviewed account_eligibility.csv; that earlier selection used >=3 conservative assessable months. This historical membership is retained by user instruction, not reapplied as an active month filter.',
            'retrospective_selection_limitation':'Full-source cohort ascertainment is not prospective admission or evidence of whole-bank generalization.'},
        'origin':'First calendar day of target month at 00:00; monthly predictors strictly earlier.',
        'reference_scale':{'months':3,'statistic':'median observed eligible-debit monthly outflow','min_debit_records_each_month':3,
            'positive_reference_required':True,'previous_month_end_snapshot_already_observed':True,
            'eligible_debits':'Known operation and type VYDAJ or VYBER; includes fees and debt payments, not a discretionary-spending map.'},
        'history':{'completed_prior_months':12,'min_mean_eligible_debits':4,'min_active_month_fraction':0.8},
        'coverage':{'full_span_month':True,'min_distinct_observed_dates':2,'max_gap_days':None,
            'meaning':'Retrospective outcome availability only; absent observed low snapshots do not prove no unobserved dips.'},
        'secondary_binary_event':{'definition':'Any observed post-transaction balance / fixed reference scale < 0.05 on a date strictly before the target month last calendar day.',
            'ratio_threshold':0.05,'operator':'<','negative_balances_included':True,'classifier_status':'exploratory' if exploratory else 'feasibility_only',
            'status_rule':'User-authorized aggregate check: exploratory when test B positive account-months <20. No threshold/split changes follow this count.'},
        'continuous_primary':{'definition':'Exact last-calendar-day closing balance / reference scale known at prediction origin.',
            'population':'All 832 registered accounts; publish exact target availability and explicit unscorable counts by assigned period.',
            'measurement':'Use a unique/equal observed balance or unique terminal vertex of a connected valid signed-ledger Euler trail. No highest-trans_id or file-order assumption.',
            'unresolved':'Preserve min/max last-day snapshot bounds; no midpoint/last-observation carry-forward, no invented scalar target. Exclude unresolved months from exact point error, not accounts from registry.',
            'derived_warning':'Predicted month-end ratio <0.05, evaluated against measured month-end ratio <0.05; distinct from secondary any-earlier low-balance event.',
            'threshold':0.05,'clipping':'None'},
        'baselines':{'last_month_ratio':'Previous exact month-end closing balance / current known reference scale (persistence on the same target denominator).',
            'pace_rule':'(Previous exact closing balance + median observed net monthly cash flow over previous 3 months) / current reference; cash flow retains bank-generated credits.',
            'logistic_regression':'Exploratory classifier for selected binary B only; not a regressor for the continuous primary target.',
            'gradient_boosting':'Regressor for the continuous primary target; separate exploratory classifier for selected B if later authorized.',
            'binary_probability_cutoff':0.5,'availability':'Report each baseline availability; paired comparisons use common exact-target/input cases without hiding missing accounts.'},
        'feature_contract':{'frequency':'monthly only','allowed':'Past monthly ratios/shares or training-fitted z-scores; all inputs known strictly before origin.',
            'recurrent_models':'No Berka daily LSTM or GRU; no recurrent Berka model in this protocol.',
            'excluded_identifiers':['account_id','client_id','counterparty account IDs'],
            'currency':'CZK retained for source arithmetic only; no raw-money predictor or PKR wallet mixing.',
            'unknown_operations':'Keep for balance/cash-flow; exclude from spending/anomaly/persona numerators and denominators.'},
        'split':{'assignment':'int(SHA256("spendsense-berka-split-v1:" + account_id),16) %100; 0..69 train, 70..84 validation, 85..99 test.',
            'file':'eval/berka_accounts/proposed_account_split.csv','sha256':sha(ROOT/'eval'/'berka_accounts'/'proposed_account_split.csv'),
            'target_periods':PARTITIONS,'cutoff_rule':'Every outcome horizon entirely inside its assigned period; past lookback may cross year boundaries only for the same assigned account.',
            'test_usage_this_step':'Aggregate positive month/account counts for A and B only, plus target availability; no prediction metrics, tuning or per-row test targets exported.'},
        'future_evaluation':{'primary':['Account-macro MAE of ratio','sqrt(account-macro mean squared ratio error)'],
            'warning':'Fixed predicted-ratio cutoff 0.05 versus month-end low-balance truth; report separately from B.',
            'secondary_exploratory':['PR-AUC','Brier score','Precision/recall/confusion counts at fixed probability 0.5'],
            'bootstrap':{'replicates':2000,'seed':20261119,'confidence':0.95,'interval':'Percentile 2.5%/97.5%',
                'resampling_unit':'Account cluster within each partition; retain all months and use the same draws for paired baseline differences.',
                'account_weighting':'Equal account weight; calculate monthly mean loss within account then aggregate accounts.',
                'undefined_binary_draws':'Record count of undefined single-class replicates; never resample until positives appear. If >5% undefined, mark that metric CI unreliable/unavailable.',
                'limitation':'Conditional on observed bank/calendar periods; not evidence of generalization to student finances.'}},
        'source_hashes':source['files'],'training_authorized':False,'model_fits':0,'pre_freeze_counts':counts,
        'target_availability':'eval/berka_low_balance/target_availability.json'}
    FREEZE.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (OUT/'protocol_v1.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (OUT/'freeze_digest.json').write_text(json.dumps({'protocol_sha256':sha(FREEZE),'cohort_sha256':sha(OUT/'cohort_832.csv'),'frozen_at':stamp},indent=2),encoding='utf-8')
    assert not development.partition.eq('test').any()
    assert len(accounts)==832 and protocol['model_fits']==0 and protocol['training_authorized'] is False
    assert assigned.B.sum()>=assigned.A.sum()
    for name,meta in source['files'].items():assert sha(ROOT/'data'/'berka_original'/name)==meta['sha256']
    print('FROZEN',stamp,'event classifier exploratory:',exploratory,flush=True)
    print('CONTINUOUS TARGET AVAILABILITY',json.dumps(quality),flush=True)


if __name__=='__main__':build()
