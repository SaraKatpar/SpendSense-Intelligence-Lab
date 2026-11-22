"""Normalize the proposal household dataset without inventing users or FX rates."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import json
from nltk.tokenize import wordpunct_tokenize

ROOT=Path(__file__).resolve().parents[1]
MAPPING={'Food':'Food','Transportation':'Transport','Household':'Groceries','subscription':'Entertainment',
         'Health':'Health','Apparel':'Shopping','Beauty':'Shopping','Education':'Education','Culture':'Entertainment',
         'Life Insurance':'Bills','Rent':'Bills','water (jar /tanker)':'Bills','maid':'Bills','Cook':'Bills',
         'garbage disposal':'Bills','Grooming':'Shopping','Tourism':'Transport','Documents':'Education'}

def main():
    raw=pd.read_csv(ROOT/'data/household_original.csv')
    input_rows=len(raw)
    raw=raw[raw['Income/Expense'].isin(['Income','Expense'])].copy()
    raw['amount']=pd.to_numeric(raw.Amount,errors='coerce')
    raw['date']=pd.to_datetime(raw.Date,dayfirst=True,errors='coerce',format='mixed').dt.normalize()
    raw=raw.dropna(subset=['amount','date'])
    raw=raw[raw.amount.gt(0)]
    # Use notes as text. Do not prepend ground-truth categories to model inputs.
    raw['description']=raw.Note.fillna('').astype(str).map(lambda t:' '.join(wordpunct_tokenize(t.lower())).strip())
    raw['category']=raw.Category.map(MAPPING).fillna('Other')
    raw['kind']=raw['Income/Expense']
    raw['merchant']=''
    raw['user_id']='household_1' # Dataset has no multi-user identifiers.
    raw['currency']='INR'
    raw[['date','amount','kind','category','description','merchant','user_id','currency']].to_csv(ROOT/'data/household_clean.csv',index=False)
    (ROOT/'data/cleaning_report.json').write_text(json.dumps({'source_rows':input_rows,'kept_rows':len(raw),'excluded_rows':input_rows-len(raw),
                'missing_notes':int(raw.description.eq('').sum()),'currency':'INR','households':1,'date_parsing':'mixed day-first formats'},indent=2))
    print(f'Prepared {len(raw)} rows. Currency INR; a single household; transfers excluded.')

if __name__=='__main__':main()
