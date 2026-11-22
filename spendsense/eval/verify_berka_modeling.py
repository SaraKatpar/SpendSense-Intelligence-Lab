"""Verify frozen definitions, CV isolation and cached test statistics; never predict."""
import sys
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'training'))
from berka_experiment import OUT,CACHE,REG_FEATURES,BINARY_FEATURES,SEED,read,save,sha,weights,verify_protocol


def main():
    protocol=verify_protocol();lock=read(OUT/'configuration_lock.json');ledger=read(OUT/'test_evaluation_ledger.json')
    assert sha(OUT/'configuration_lock.json')==ledger['configuration_lock_sha256']==read(OUT/'configuration_lock_digest.json')['sha256']
    assert lock['locked_at']<=ledger['started_at'] and ledger['status']=='complete'
    assert ledger['evaluation_passes']==1 and all(n==1 for n in ledger['estimator_prediction_calls'].values())
    assert sha(OUT/'test_predictions_ONCE.csv')==ledger['saved_predictions_sha256']
    for name,meta in protocol['source_hashes'].items():assert sha(ROOT/'data/berka_original'/name)==meta['sha256']
    dev=pd.read_csv(CACHE/'development.csv');test=pd.read_csv(OUT/'test_predictions_ONCE.csv')
    assert dev.partition.isin(['train','validation']).all()
    assert pd.to_datetime(dev.feature_latest_date).lt(pd.to_datetime(dev.month_start)).all()
    assert pd.to_datetime(dev.month_end).max()<pd.Timestamp('1998-01-01')
    test_accounts=set(test.account_id)
    assert not set(dev.account_id)&test_accounts
    for name,record in lock['models'].items():
        assert sha(record['file'])==record['sha256']
        bundle=joblib.load(record['file']);assert not set(bundle['train_accounts'])&test_accounts
        source=dev[dev.month_end_ratio.notna()] if record['role']=='regression' else dev
        assert set(bundle['features'])==set(REG_FEATURES if record['role']=='regression' else BINARY_FEATURES)
        assert all(x.endswith('_ratio') for x in bundle['features'])
        expected=np.average(source[bundle['features']],axis=0,weights=weights(source.account_id))
        assert np.allclose(expected,bundle['scaler'].mean_)
    folds=pd.read_csv(OUT/'cv_account_groups.csv').set_index('account_id').cv_group
    reg=read(OUT/'regression_cv.json');binary=read(OUT/'binary_cv.json')
    counts_cv=0
    for record in reg['candidates']+binary['logistic_candidates']+[binary['shallow_booster_candidate']]:
        for fold in record['folds']:
            if 'skipped' in fold:continue
            group=int(fold['fold'].split('_')[0].replace('group',''));year=int(fold['fold'].split('_year')[1])
            years=pd.to_datetime(dev.month_start).dt.year
            a=dev[dev.account_id.map(folds).ne(group)&years.lt(year)]
            b=dev[dev.account_id.map(folds).eq(group)&years.eq(year)]
            if record['spec']['kind'] not in ('logistic','gbc'):a=a[a.month_end_ratio.notna()];b=b[b.month_end_ratio.notna()]
            assert len(a)==fold['train_months'] and len(b)==fold['validation_months']
            assert not set(a.account_id)&set(b.account_id)
            assert pd.to_datetime(a.month_end).max()<pd.to_datetime(b.month_start).min()
            counts_cv+=1
    assert int(test.low_balance_event_B.sum())==7 and test.loc[test.low_balance_event_B,'account_id'].nunique()==4
    metrics=read(OUT/'regression_results.json');common=test[test.month_end_ratio.notna()].dropna(subset=['persistence','pace','linear','ridge','gradient_boosting'])
    ids=np.sort(common.account_id.unique());n=len(ids)
    rng=np.random.default_rng(SEED);draws=rng.multinomial(n,np.full(n,1/n),size=2000)
    saved=pd.read_csv(OUT/'regression_bootstrap_draws.csv')
    for model,record in metrics['paired_common_cases'].items():
        loss=(common[model]-common.month_end_ratio)
        per_account=pd.DataFrame({'account':common.account_id,'abs':loss.abs(),'squared':loss**2}).groupby('account').mean().reindex(ids)
        a=draws@per_account['abs'].to_numpy()/n;s=np.sqrt(draws@per_account.squared.to_numpy()/n)
        assert np.allclose(a,saved[model+'_mae']) and np.allclose(s,saved[model+'_rmse'])
        assert np.allclose(np.quantile(a,[.025,.975]),record['mae_ci95'])
        assert np.allclose(np.quantile(s,[.025,.975]),record['rmse_ci95'])
    for model,record in metrics['primary_all_available_cases'].items():
        subset=test[test.month_end_ratio.notna() & test[model].notna()]
        delta=subset[model]-subset.month_end_ratio
        grouped=pd.DataFrame({'account':subset.account_id,'abs':delta.abs(),'sq':delta**2}).groupby('account').mean()
        count=len(grouped);sample=np.random.default_rng(SEED).multinomial(count,np.full(count,1/count),size=2000)
        absolute=sample@grouped['abs'].to_numpy()/count
        squared=np.sqrt(sample@grouped.sq.to_numpy()/count)
        assert np.isclose(record['mae'],grouped['abs'].mean()) and np.isclose(record['rmse'],np.sqrt(grouped.sq.mean()))
        assert np.allclose(record['mae_ci95'],np.quantile(absolute,[.025,.975]))
        assert np.allclose(record['rmse_ci95'],np.quantile(squared,[.025,.975]))
        assert record['months']==len(subset) and record['accounts']==count
    binary_metrics=read(OUT/'exploratory_binary_results.json')
    for name,value in binary_metrics.items():
        boot=pd.read_csv(OUT/(name+'_bootstrap_draws.csv'))
        assert len(boot)==2000 and int(boot.zero_positive.sum())==value['zero_positive_draws']==34
        assert int(boot.average_precision.isna().sum())==34
        assert int(boot.brier.isna().sum())==0
        assert int(boot.precision_at_0_5.isna().sum())==728
        assert value['intervals']['precision_at_0_5']['ci95'] is None
    bias=pd.read_csv(OUT/'account_selection_bias.csv')
    assert len(bias)==832 and bias.scorable.sum()==639 and (~bias.scorable).sum()==193
    expected={'train':(400,177),'validation':(97,16),'test':(142,0)}
    for name,(yes,no) in expected.items():assert int((bias.partition.eq(name)&bias.scorable).sum())==yes and int((bias.partition.eq(name)&~bias.scorable).sum())==no
    result={'passed':True,'frozen_protocol_unchanged':True,'definition_threshold_coverage_split_unchanged':True,
        'verified_forward_account_disjoint_cv_fits':counts_cv,'final_development_refits':len(lock['models']),
        'preprocessing_fit_on_development_only':True,'monthly_dimensionless_features_only':True,'test_passes':1,
        'test_estimator_prediction_calls':ledger['estimator_prediction_calls'],'independent_cached_bootstrap_reconstruction':True,
        'binary_zero_positive_draws':34,'precision_undefined_draws':728,'selection_bias_accounts':{'scorable':639,'unscorable':193},
        'no_test_retuning':True,'verification_used_predict_or_fit':False}
    save(OUT/'verification.json',result);print(result)


if __name__=='__main__':main()
