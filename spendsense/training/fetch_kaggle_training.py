"""Download selected public Kaggle files; preserve provenance and units.
Requires requests, pandas, openpyxl, nltk. Does not execute downloaded code.
"""
import sys,json,zipfile,io,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests,pandas as pd
from nltk.tokenize import wordpunct_tokenize
from storage import ROOT
from training.prepare_household import MAPPING

PERSONAL_MAP={'Groceries':'Groceries','Restaurants':'Food','Coffee Shops':'Food','Fast Food':'Food','Food & Dining':'Food','Shopping':'Shopping','Electronics & Software':'Shopping','Haircut':'Shopping','Utilities':'Bills','Mortgage & Rent':'Bills','Mobile Phone':'Bills','Internet':'Bills','Auto Insurance':'Bills','Gas & Fuel':'Transport','Music':'Entertainment','Movies & Dvds':'Entertainment','Television':'Entertainment','Entertainment':'Entertainment','Alcohol & Bars':'Entertainment','Home Improvement':'Other'}

def fetch(ref,folder):
    folder.mkdir(exist_ok=True,parents=True)
    response=requests.get('https://www.kaggle.com/api/v1/datasets/view/'+ref,timeout=30);response.raise_for_status();meta=response.json()
    (folder/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    response=requests.get('https://www.kaggle.com/api/v1/datasets/download/'+ref,timeout=60);response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for item in archive.infolist():
            if item.filename.lower().endswith(('.csv','.xlsx')):
                if item.file_size>20_000_000:raise ValueError('Unexpectedly large source file')
                (folder/Path(item.filename).name).write_bytes(archive.read(item))
    return meta


def main():
    target=ROOT/'data/kaggle';target.mkdir(exist_ok=True)
    personal=fetch('entrepreneurlife/personal-finance',target/'personal-finance')
    household=fetch('soumojit11/daily-household-transactions',target/'daily-household-transactions')
    raw=pd.read_excel(next((target/'personal-finance').glob('*.xlsx')))
    selected=raw[(raw['Transaction Type'].str.lower()=='debit')&raw.Category.isin(PERSONAL_MAP)].copy()
    clean=pd.DataFrame({'user_id':'kaggle_personal_reference_1','date':pd.to_datetime(selected.Date).dt.strftime('%Y-%m-%d'),'amount':selected.Amount.astype(float),'kind':'Expense','category':selected.Category.map(PERSONAL_MAP),'description':selected.Description.map(lambda t:' '.join(wordpunct_tokenize(str(t).lower()))),'merchant':'','currency':'UNSPECIFIED_SOURCE_UNITS'})
    clean=clean[clean.amount>0].drop_duplicates();clean.to_csv(target/'personal_reference_clean.csv',index=False)
    reference=pd.read_csv(next((target/'daily-household-transactions').glob('*.csv')))
    reference=reference[reference['Income/Expense'].isin(['Income','Expense'])].copy()
    reference['date']=pd.to_datetime(reference.Date,dayfirst=True,format='mixed',errors='coerce').dt.normalize()
    reference['amount']=pd.to_numeric(reference.Amount,errors='coerce');reference['kind']=reference['Income/Expense'];reference['category']=reference.Category.map(MAPPING).fillna('Other');reference['description']=reference.Note.fillna('').map(lambda t:' '.join(wordpunct_tokenize(str(t).lower())).strip());reference['user_id']='household_1';reference['merchant']='';reference['currency']='INR'
    reference=reference.dropna(subset=['date','amount']);reference=reference[reference.amount>0]
    combined=pd.concat([reference[list(clean.columns)],clean],ignore_index=True)
    expense=combined[combined.kind=='Expense'];conflicts=expense.groupby('description').category.nunique();bad=set(conflicts[conflicts>1].index)
    combined=combined[~combined.description.isin(bad)];combined['date']=pd.to_datetime(combined.date,format='mixed').dt.strftime('%Y-%m-%d');combined.to_csv(target/'categorizer_training.csv',index=False)
    result={'selected_clean_expenses':len(clean),'excluded_rows':len(raw)-len(clean),'classifier_conflicting_descriptions_removed':len(bad),'classifier_rows_after_conflict_removal':len(combined),'currency':'Personal source units unspecified, never converted to PKR; classifier consumes text only','sources':[{'ref':'entrepreneurlife/personal-finance','license_as_reported':personal.get('licenseName')},{'ref':'soumojit11/daily-household-transactions','license_as_reported':household.get('licenseName')}],'files':[]}
    for path in target.rglob('*'):
        if path.is_file() and path.name not in ['reproduction_manifest.json','audit.json']:result['files'].append({'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (target/'reproduction_manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
if __name__=='__main__':main()
