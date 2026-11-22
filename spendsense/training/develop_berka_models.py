"""Development-only grouped forward CV; locks configurations before test scoring."""
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import average_precision_score
from berka_experiment import OUT,CACHE,MODELS,REG_FEATURES,BINARY_FEATURES,SEED,preregister,verify_protocol,read,save,sha,stamp,fit,predict,reg_metrics,macro_brier,weights


def folds(data):
    ids=np.sort(data.account_id.unique());splitter=GroupKFold(n_splits=3,shuffle=True,random_state=SEED)
    result=[];assignment=[]
    years=pd.to_datetime(data.month_start).dt.year
    for number,(_,held_indices) in enumerate(splitter.split(ids,groups=ids)):
        held=set(ids[held_indices]);assignment.extend({'account_id':int(x),'cv_group':number} for x in held)
        for year in (1995,1996,1997):
            train=data[~data.account_id.isin(held)&years.lt(year)]
            valid=data[data.account_id.isin(held)&years.eq(year)]
            if train.empty or valid.empty:continue
            assert not set(train.account_id)&set(valid.account_id)
            assert pd.to_datetime(train.month_end).max()<pd.to_datetime(valid.month_start).min()
            result.append((f'group{number}_year{year}',train.index.to_numpy(),valid.index.to_numpy()))
    pd.DataFrame(assignment).sort_values('account_id').to_csv(OUT/'cv_account_groups.csv',index=False)
    return result


def cv(spec,data,folds_,target,features):
    predictions=[];diagnostics=[];messages=[]
    for name,train_index,valid_index in folds_:
        training=data.loc[train_index];validation=data.loc[valid_index]
        if target=='month_end_ratio':
            training=training[training.month_end_ratio.notna()];validation=validation[validation.month_end_ratio.notna()]
        if training.empty or validation.empty:continue
        if target=='low_balance_event_B' and training[target].nunique()<2:
            diagnostics.append({'fold':name,'skipped':'Single-class training data; no fabricated positive or fallback classifier.'});continue
        with warnings.catch_warnings(record=True) as caught:
            bundle=fit(spec,training,target,features)
            result=predict(bundle,validation)
        messages.extend({'fold':name,'warning':str(item.message)} for item in caught)
        part=validation[['account_id','month_id',target]].copy();part['row_id']=validation.index;part['prediction']=result;part['fold']=name
        predictions.append(part)
        diagnostics.append({'fold':name,'train_accounts':int(training.account_id.nunique()),'validation_accounts':int(validation.account_id.nunique()),
            'train_months':len(training),'validation_months':len(validation),'train_target_end':str(pd.to_datetime(training.month_end).max().date()),
            'validation_target_start':str(pd.to_datetime(validation.month_start).min().date()),
            'train_binary_positives':int(training.low_balance_event_B.sum()),'validation_binary_positives':int(validation.low_balance_event_B.sum())})
    oof=pd.concat(predictions,ignore_index=True).set_index('row_id').sort_index()
    assert oof.index.is_unique
    score=reg_metrics(oof.account_id,oof[target],oof.prediction) if target=='month_end_ratio' else {
        'brier':macro_brier(oof.account_id,oof[target],oof.prediction),
        'account_weighted_average_precision':float(average_precision_score(oof[target],oof.prediction,sample_weight=weights(oof.account_id)))}
    return oof,{'spec':spec,'score':score,'accounts':int(oof.account_id.nunique()),'months':len(oof),'folds':diagnostics,'warnings':messages}


def main():
    plan=preregister();verify_protocol()
    if (OUT/'configuration_lock.json').exists():raise SystemExit('Configurations already locked. No retuning is permitted after the test pass.')
    manifest=read(OUT/'dataset_manifest.json')
    assert sha(CACHE/'development.csv')==manifest['development_sha256']
    assert sha(CACHE/'sealed_test.csv')==manifest['sealed_test_sha256']  # Integrity only, never read test values.
    data=pd.read_csv(CACHE/'development.csv')
    assert data.partition.isin(['train','validation']).all()
    folds_=folds(data);save(OUT/'cv_design.json',{'method':plan['cv'],'folds':len(folds_),'fixed_validation_set_not_used_alone':True})
    reg_oof={};reg_records=[]
    for spec in plan['regression_candidates']:
        oof,record=cv(spec,data,folds_,'month_end_ratio',REG_FEATURES)
        reg_oof[spec['name']]=oof;reg_records.append(record)
        print('Regression CV',spec['name'],record['score'],flush=True)
    chosen={}
    for kind in ('linear','ridge','gbr'):
        chosen[kind]=min([x for x in reg_records if x['spec']['kind']==kind],key=lambda x:x['score']['mae'])
    reg_comparison=pd.DataFrame(index=reg_oof[chosen['linear']['spec']['name']].index)
    for name,column in [('persistence','persistence'),('pace','pace')]:reg_comparison[name]=data.loc[reg_comparison.index,column]
    labels={'linear':'linear','ridge':'ridge','gbr':'gradient_boosting'}
    for kind,record in chosen.items():reg_comparison[labels[kind]]=reg_oof[record['spec']['name']].prediction
    common=reg_comparison.dropna()
    common_scores={name:reg_metrics(data.loc[common.index,'account_id'],data.loc[common.index,'month_end_ratio'],common[name]) for name in common.columns}
    preference=min(common_scores,key=lambda name:common_scores[name]['mae'])
    reg_comparison.join(data[['account_id','month_id','month_end_ratio']]).to_csv(OUT/'development_oof_regression.csv',index_label='row_id')
    save(OUT/'regression_cv.json',{'candidates':reg_records,'selected_within_family':chosen,'common_case_comparison':common_scores,'development_preference':preference,
        'common_accounts':int(data.loc[common.index,'account_id'].nunique()),'common_months':len(common),'selection_used_test':False})

    binary_oof={};binary_records=[]
    for spec in plan['logistic_candidates']:
        oof,record=cv(spec,data,folds_,'low_balance_event_B',BINARY_FEATURES)
        binary_oof[spec['name']]=oof;binary_records.append(record)
        print('Exploratory logistic CV',spec['name'],record['score'],flush=True)
    best_score=min(x['score']['brier'] for x in binary_records)
    selected_logistic=min([x for x in binary_records if x['score']['brier']<=best_score+1e-6],key=lambda x:x['spec']['params']['C'])
    booster_oof,booster_record=cv(plan['binary_boost_candidate'],data,folds_,'low_balance_event_B',BINARY_FEATURES)
    logistic_oof=binary_oof[selected_logistic['spec']['name']]
    ids=logistic_oof.index.intersection(booster_oof.index)
    shared=data.loc[ids];lr=logistic_oof.loc[ids,'prediction'];gb=booster_oof.loc[ids,'prediction']
    losses=pd.DataFrame({'account_id':shared.account_id,'difference':(gb-shared.low_balance_event_B.astype(int))**2-(lr-shared.low_balance_event_B.astype(int))**2}).groupby('account_id').difference.mean()
    n=len(losses);draws=np.random.default_rng(SEED).multinomial(n,np.full(n,1/n),size=2000)
    difference_ci=np.quantile(draws@losses.to_numpy()/n,[.025,.975]).tolist()
    lr_brier=macro_brier(shared.account_id,shared.low_balance_event_B,lr);gb_brier=macro_brier(shared.account_id,shared.low_balance_event_B,gb)
    lr_ap=float(average_precision_score(shared.low_balance_event_B,lr,sample_weight=weights(shared.account_id)))
    gb_ap=float(average_precision_score(shared.low_balance_event_B,gb,sample_weight=weights(shared.account_id)))
    gate={'relative_brier_improvement':float((lr_brier-gb_brier)/lr_brier),'paired_brier_difference_ci95':difference_ci,
        'average_precision_not_decreased':gb_ap>=lr_ap,'test_used':False}
    retain_boost=bool(gate['relative_brier_improvement']>=.05 and difference_ci[1]<0 and gb_ap>=lr_ap)
    gate['retained']=retain_boost
    save(OUT/'binary_cv.json',{'logistic_candidates':binary_records,'selected_logistic':selected_logistic,'shallow_booster_candidate':booster_record,'boost_gate':gate,
        'fixed_validation_subset_not_used_for_tuning':True,'status':'EXPLORATORY','no_oversampling_or_synthetic_rows':True})
    binary_records_frame=pd.DataFrame({'account_id':shared.account_id,'month_id':shared.month_id,'truth':shared.low_balance_event_B,'logistic':lr,'shallow_boost_diagnostic':gb})
    binary_records_frame.to_csv(OUT/'development_oof_binary.csv',index_label='row_id')

    files={};reg_fit=data[data.month_end_ratio.notna()]
    for kind,record in chosen.items():
        name=labels[kind];bundle=fit(record['spec'],reg_fit,'month_end_ratio',REG_FEATURES)
        file=MODELS/(name+'.joblib');joblib.dump(bundle,file)
        files[name]={'file':str(file),'sha256':sha(file),'role':'regression','spec':record['spec']}
    bundle=fit(selected_logistic['spec'],data,'low_balance_event_B',BINARY_FEATURES)
    file=MODELS/'logistic_regularized.joblib';joblib.dump(bundle,file)
    files['logistic_regularized']={'file':str(file),'sha256':sha(file),'role':'exploratory_binary','spec':selected_logistic['spec']}
    if retain_boost:
        bundle=fit(plan['binary_boost_candidate'],data,'low_balance_event_B',BINARY_FEATURES)
        file=MODELS/'binary_gradient_boosting.joblib';joblib.dump(bundle,file)
        files['binary_gradient_boosting']={'file':str(file),'sha256':sha(file),'role':'exploratory_binary','spec':plan['binary_boost_candidate']}
    lock={'locked_at':stamp(),'protocol_sha256':plan['protocol_sha256'],'plan_sha256':sha(OUT/'training_authorization_and_plan.json'),
        'development_sha256':manifest['development_sha256'],'sealed_test_sha256':manifest['sealed_test_sha256'],'models':files,
        'regression_baselines':['persistence','pace'],'development_preference':preference,'binary_boost_retained':retain_boost,
        'regression_cv_sha256':sha(OUT/'regression_cv.json'),'binary_cv_sha256':sha(OUT/'binary_cv.json'),
        'test_metrics_seen':False,'fit_scope':'Pooled original train+validation periods, no test accounts; new user authorization recorded separately from frozen historical no-training snapshot.'}
    save(OUT/'configuration_lock.json',lock);save(OUT/'configuration_lock_digest.json',{'sha256':sha(OUT/'configuration_lock.json')})
    print('CONFIGURATIONS LOCKED BEFORE TEST',lock['locked_at'],'development preference:',preference,'binary boost retained:',retain_boost,flush=True)


if __name__=='__main__':main()
