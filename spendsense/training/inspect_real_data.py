"""Step 1 only: inspect original files, without cleaning, imputing or training.

Example (from spendsense):
python training/inspect_real_data.py --csv data/household_original.csv --output eval/household_audit.json
"""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd


def inspect(path,separator=','):
    frame=pd.read_csv(path,sep=separator)
    result={'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(frame),'columns':list(frame.columns),
            'dtypes':frame.dtypes.astype(str).to_dict(),'missing':{k:int(v) for k,v in frame.isna().sum().items()},
            'exact_duplicate_rows':int(frame.duplicated().sum()),'transformation':'None: input file is only read.',
            'provenance':'Dataset identity and real-world collection must be confirmed from original source documentation; file statistics do not prove authenticity.'}
    # Inspect these fields only after checking that they actually exist.
    for column in ('Income/Expense','Currency','Category','Mode'):
        if column in frame:result[column+'_counts']={str(k):int(v) for k,v in frame[column].value_counts(dropna=False).items()}
    if 'Amount' in frame:
        values=pd.to_numeric(frame['Amount'],errors='coerce')
        result['amount']={'invalid':int(values.isna().sum()),'zero':int(values.eq(0).sum()),'negative':int(values.lt(0).sum()),
                          'minimum':float(values.min()),'median':float(values.median()),'maximum':float(values.max())}
    if 'Date' in frame:
        values=pd.to_datetime(frame['Date'],format='mixed',dayfirst=True,errors='coerce')
        result['date']={'parse_assumption':'day-first mixed dates, for audit only; original strings are preserved',
            'invalid':int(values.isna().sum()),'first':str(values.min()),'last':str(values.max()),'distinct_days':int(values.dt.normalize().nunique()),
            'calendar_days':int((values.max().normalize()-values.min().normalize()).days+1)}
    if 'Note' in frame:
        notes=frame['Note'].fillna('').astype(str).str.strip().str.lower()
        result['text']={'missing_or_blank_notes':int(notes.eq('').sum()),'distinct_nonempty_notes':int(notes[notes.ne('')].nunique()),
                        'normalization_for_counting_only':'strip surrounding whitespace and lowercase; no training data written'}
        if 'Category' in frame:
            counts=frame.loc[notes.ne('')].assign(audit_note=notes[notes.ne('')]).groupby('audit_note')['Category'].nunique()
            result['text']['notes_with_multiple_category_labels']=int(counts.gt(1).sum())
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',type=Path,required=True);parser.add_argument('--sep',default=',')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=inspect(args.csv,args.sep);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
