"""Seal one future, text-disjoint benchmark before personalization/candidate fits.

Does not evaluate any model or touch Berka. Old candidate artifacts are excluded:
they previously saw overlapping source data and cannot claim untouched testing.
"""
import hashlib,json,sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from app.personalization import normalize
from training.real_source_policy import require_real_csv
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval/category_benchmark_v1'
CACHE=ROOT.parent/'work/category_benchmark_v1'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    if (OUT/'split_lock.json').exists():
        print('Split already sealed; no rewrite.');return
    records=[];sources={}
    for source,name in [('household','data/household_clean.csv'),('personal','data/kaggle/personal_reference_clean.csv')]:
        path=require_real_csv(ROOT/name);sources[name]=sha(path)
        frame=pd.read_csv(path,keep_default_na=False);frame['date']=pd.to_datetime(frame.date)
        frame=frame.loc[frame.kind.eq('Expense')].copy()
        frame['normalized']=frame.description.map(normalize)
        frame=frame.loc[frame.normalized.str.len().ge(3)].copy()
        frame['source']=source;frame['row_id']=[f'{source}:{i}' for i in frame.index]
        dates=sorted(frame.date.unique())
        cut=[pd.Timestamp(dates[min(len(dates)-1,int(len(dates)*p))]) for p in (.6,.7,.8)]
        frame['partition']='test'
        frame.loc[frame.date.lt(cut[2]),'partition']='curve_evaluation'
        frame.loc[frame.date.lt(cut[1]),'partition']='correction'
        frame.loc[frame.date.lt(cut[0]),'partition']='train'
        records.append(frame[['row_id','source','date','description','normalized','category','partition']])
    all_rows=pd.concat(records,ignore_index=True).sort_values(['date','source','row_id'])
    test=all_rows.loc[all_rows.partition.eq('test')].copy()
    dev=all_rows.loc[~all_rows.partition.eq('test')].copy()
    # Test text is used only for purge membership, never to fit vocabulary or to
    # inspect/tune on its labels. Every future test description is novel to all
    # newly fitted candidates and every personalization correction.
    purged=dev.normalized.isin(set(test.normalized))
    removed=dev.loc[purged].copy();dev=dev.loc[~purged].copy()
    assert not set(dev.normalized)&set(test.normalized)
    dev.to_csv(CACHE/'development.csv',index=False)
    test.to_csv(CACHE/'sealed_test.csv',index=False)
    removed[['row_id','source','date','partition']].to_csv(OUT/'purged_development_ids.csv',index=False)
    pd.concat([dev,test])[['row_id','source','date','partition']].to_csv(OUT/'split_ids.csv',index=False)
    lock={'timestamp':datetime.now(ZoneInfo('Asia/Karachi')).isoformat(),
        'protocol':'Per-source unique-date boundaries 60/70/80%; all earlier rows with any sealed-test normalized description purged from development. Same-day rows never cross a source boundary.',
        'step4':'Global fit=train only; correction feedback=next 10% dates; fixed future learning-curve evaluation=following 10%; final 20% dates reserved exclusively for step5.',
        'source_hashes':sources,'development_sha256':sha(CACHE/'development.csv'),'sealed_test_sha256':sha(CACHE/'sealed_test.csv'),
        'development_rows':len(dev),'sealed_test_rows':len(test),'purged_development_rows':len(removed),
        'development_counts':{str(k):int(v) for k,v in dev.groupby(['source','partition']).size().items()},
        'test_labels_inspected_for_model_selection':False,
        'historical_warning':'Older models/evaluations used overlapping raw sources; discard their weights for the untouched comparison. This is a newly sealed model-untouched experiment, not a newly collected or historically unseen dataset.',
        'privacy':'Public reference records only; no personal app database or Berka inputs.'}
    (OUT/'split_lock.json').write_text(json.dumps(lock,indent=2),encoding='utf-8')
    print(json.dumps({k:lock[k] for k in ('development_rows','sealed_test_rows','purged_development_rows','development_counts')},indent=2))


if __name__=='__main__':main()
