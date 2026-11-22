"""Validate eligibility rules against the real original table, never fake rows."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.data.berka_policy import label_rows,rows_for,UNKNOWN_ROLE


def check(folder):
    frame=pd.read_csv(folder/'trans.asc',sep=';',keep_default_na=False)
    labeled=label_rows(frame)
    pd.testing.assert_frame_equal(labeled.drop(columns=['record_role']),frame)
    missing=labeled.record_role.eq(UNKNOWN_ROLE)
    assert int(missing.sum())==183114
    assert labeled.loc[missing,'type'].eq('PRIJEM').all()
    assert labeled.loc[missing,'k_symbol'].eq('UROK').all()
    checks={}
    for purpose in ('cash_flow','balance','spending','anomaly','persona'):
        rows=rows_for(frame,purpose)
        all_rows=purpose in ('cash_flow','balance')
        assert len(rows)==(len(frame) if all_rows else len(frame)-183114)
        if all_rows:assert rows.amount.sum()==frame.amount.sum()
        else:assert not rows.record_role.eq(UNKNOWN_ROLE).any()
        checks[purpose]={'rows':len(rows),'unknown_operation_rows':int(rows.record_role.eq(UNKNOWN_ROLE).sum())}
    proof=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    for filename,metadata in proof['files'].items():
        assert hashlib.sha256((folder/filename).read_bytes()).hexdigest()==metadata['sha256']
    return {'source':'Original real Berka trans.asc; no generated test rows','passed':True,'raw_files_unchanged':True,
        'checks':checks,'training_run':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,default=Path('data/berka_original'))
    parser.add_argument('--output',type=Path,default=Path('eval/berka_policy_checks.json'))
    args=parser.parse_args();result=check(args.folder);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
