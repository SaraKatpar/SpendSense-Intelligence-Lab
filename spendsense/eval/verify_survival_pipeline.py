"""Saved-output reconstruction only; no fit/predict calls or Berka reads."""
import hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval/survival_pipeline_v1'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    lock=json.loads((OUT/'configuration_lock.json').read_text())
    ledger=json.loads((OUT/'evaluation_ledger.json').read_text())
    assert ledger['status']=='complete' and ledger['passes']==1
    assert sha(OUT/'configuration_lock.json')==ledger['configuration_lock_sha256']
    assert sha(OUT/'daily_predictions.csv')==ledger['daily_predictions_sha256']
    daily=pd.read_csv(OUT/'daily_predictions.csv')
    windows=pd.read_csv(OUT/'window_predictions.csv')
    metrics=pd.read_csv(OUT/'metrics.csv')
    for source,spec in lock.items():
        path=ROOT/spec['source'];assert sha(path)==spec['source_sha256']
        assert sha(ROOT/spec['model_path']/'forecast.pt')==spec['model_sha256']
        raw=pd.read_csv(path);actual=raw.loc[raw.kind.eq('Expense')].groupby('date').amount.sum()
        selected=daily.loc[daily.source.eq(source)]
        assert selected.origin.min()>=spec['evaluation_start']>spec['training_end']
        for row in selected.itertuples():
            assert np.isclose(row.actual_recorded_daily_total,actual.get(row.date,0))
            assert row.date>=row.origin
        for model,rows in selected.groupby('model'):
            blocks=windows.loc[windows.source.eq(source)&windows.model.eq(model)]
            assert len(rows)==len(blocks)*14
            for origin,group in rows.groupby('origin'):
                assert len(group)==14
                block=blocks.loc[blocks.origin.eq(origin)].iloc[0]
                assert np.isclose(block.conditional_final_balance_error,(group.actual_recorded_daily_total-group.prediction).sum())
            error=rows.prediction-rows.actual_recorded_daily_total
            metric=metrics.loc[metrics.source.eq(source)&metrics.model.eq(model)].iloc[0]
            assert np.isclose(metric.daily_total_mae,error.abs().mean())
            assert np.isclose(metric.daily_total_rmse,np.sqrt((error**2).mean()))
            assert np.isclose(metric.conditional_final_balance_mae,blocks.conditional_final_balance_error.abs().mean())
            assert np.isclose(metric.conditional_final_balance_rmse,np.sqrt((blocks.conditional_final_balance_error**2).mean()))
    assert windows.actual_exhaustion_date.isna().all()
    assert metrics.exhaustion_date_error.isna().all()
    result={'passed':True,'saved_metrics_reconstructed':True,'raw_recorded_daily_truth_checked':True,
        'source_currency_isolation':True,'opening_cash_or_exhaustion_labels_invented':False,
        'exhaustion_date_validation':'Unavailable, not claimed','full_survival_validated':False,
        'fit_or_predict_called':False}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
