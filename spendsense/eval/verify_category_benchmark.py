"""Independent saved-prediction checks; never calls fit or predict."""
import hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from storage import CATEGORIES
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval/category_benchmark_v1'
MODELS=ROOT/'models/category_benchmark_v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lock=json.loads((OUT/'configuration_lock.json').read_text())
    ledger=json.loads((OUT/'test_evaluation_ledger.json').read_text())
    split=json.loads((OUT/'split_lock.json').read_text())
    assert ledger['status']=='complete' and ledger['passes']==1
    assert ledger['configuration_lock_sha256']==sha(OUT/'configuration_lock.json')
    assert ledger['predictions_sha256']==sha(OUT/'test_predictions_ONCE.csv')
    for name,digest in lock['artifacts'].items():assert sha(MODELS/name)==digest
    cache=ROOT.parent/'work/category_benchmark_v1'
    assert sha(cache/'development.csv')==split['development_sha256']
    dev=pd.read_csv(cache/'development.csv',keep_default_na=False)
    test=pd.read_csv(OUT/'test_predictions_ONCE.csv',keep_default_na=False)
    ids=pd.read_csv(OUT/'split_ids.csv')
    assert test.row_id.tolist()==ids.loc[ids.partition.eq('test'),'row_id'].tolist()
    assert set(dev.row_id)==set(lock['development_training_row_ids'])
    assert not set(dev.row_id)&set(test.row_id)
    assert not set(dev.normalized)&set(test.normalized)
    for source,rows in dev.groupby('source'):
        assert rows.date.max()<test.loc[test.source.eq(source),'date'].min()
    training_hash=hashlib.sha256('\n'.join(lock['development_training_row_ids']).encode()).hexdigest()
    for name in ('distilbert_head','distilbert_last2'):
        meta=json.loads((MODELS/name/'training.json').read_text())
        assert meta['training_row_ids_sha256']==training_hash and meta['test_rows_seen']==0
    metrics=json.loads((OUT/'metrics.json').read_text())
    for model in lock['candidate_names']:
        assert ledger['dataset_prediction_passes'][model]==1
        assert test[model].isin(CATEGORIES).all()
        for source,rows in [('all',test),*list(test.groupby('source'))]:
            actual=metrics['results'][model][source]
            assert np.isclose(actual['accuracy'],rows.category.eq(rows[model]).mean())
            f=[]
            for category in CATEGORIES:
                tp=((rows.category==category)&(rows[model]==category)).sum()
                fp=((rows.category!=category)&(rows[model]==category)).sum()
                fn=((rows.category==category)&(rows[model]!=category)).sum()
                f.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.)
            assert np.isclose(actual['macro_f1_fixed_9_classes'],np.mean(f))
    protected=json.loads((ROOT/'eval/spending_mix_v1/protected_berka_hashes.json').read_text())
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    result={'passed':True,'test_rows':len(test),'unique_test_descriptions':test.normalized.nunique(),
        'all_models_same_test_row_ids':True,'all_models_same_training_row_ids':True,
        'no_description_overlap':True,'source_chronology_verified':True,'independent_metric_reconstruction':True,
        'frozen_berka_artifacts_unchanged':True,'fit_or_predict_called':False}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
