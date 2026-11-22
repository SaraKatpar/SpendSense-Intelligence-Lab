"""One test prediction pass, after the immutable development configuration lock."""
import json
import joblib
import numpy as np
import pandas as pd
from berka_experiment import OUT,CACHE,read,save,sha,stamp,verify_protocol,predict


def main():
    verify_protocol()
    lock_path=OUT/'configuration_lock.json';lock=read(lock_path)
    assert sha(lock_path)==read(OUT/'configuration_lock_digest.json')['sha256']
    assert sha(OUT/'training_authorization_and_plan.json')==lock['plan_sha256']
    assert sha(CACHE/'development.csv')==lock['development_sha256']
    assert sha(CACHE/'sealed_test.csv')==lock['sealed_test_sha256']
    for record in lock['models'].values():assert sha(record['file'])==record['sha256']
    ledger_path=OUT/'test_evaluation_ledger.json'
    # Exclusive creation precedes opening test values or making predictions.
    with ledger_path.open('x',encoding='utf-8') as handle:
        json.dump({'status':'started','started_at':stamp(),'evaluation_passes':1,'configuration_lock_sha256':sha(lock_path)},handle,indent=2)
    test=pd.read_csv(CACHE/'sealed_test.csv')
    assert test.partition.eq('test').all() and pd.to_datetime(test.month_start).dt.year.eq(1998).all()
    assert int(test.low_balance_event_B.sum())==7
    result=test[['account_id','month_id','month_start','month_end','month_end_ratio','low_balance_event_B','persistence','pace']].copy()
    calls={}
    for name,record in lock['models'].items():
        bundle=joblib.load(record['file'])
        assert not set(bundle['train_accounts'])&set(test.account_id)
        values=predict(bundle,test)
        assert np.isfinite(values).all()
        result[name]=values;calls[name]=1
    result.to_csv(OUT/'test_predictions_ONCE.csv',index=False)
    save(ledger_path,{'status':'complete','started_at':read(ledger_path)['started_at'],'completed_at':stamp(),
        'evaluation_passes':1,'estimator_prediction_calls':calls,'configuration_lock_sha256':sha(lock_path),
        'test_input_sha256':sha(CACHE/'sealed_test.csv'),'saved_predictions_sha256':sha(OUT/'test_predictions_ONCE.csv'),
        'rule':'Do not rerun models on test. Metrics/plots read these saved predictions. No post-test retuning.'})
    print('Completed the single locked test prediction pass. Future reporting uses cached predictions only.',flush=True)


if __name__=='__main__':main()
