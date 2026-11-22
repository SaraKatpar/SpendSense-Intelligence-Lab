"""Refresh only the real observed WFP market-price manifest."""
import json,hashlib
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def main():
    path=ROOT/'data/wfp_food_prices_pak.csv'
    item={'name':'WFP Pakistan market prices','file':path.name,
          'source':'https://data.humdata.org/dataset/wfp-food-prices-for-pakistan',
          'use':'Observed market-price reference only; not spending-model training.',
          'limits':'PKR retail observations; no Sukkur/canteen coverage or currency conversion.',
          'rows':len(pd.read_csv(path)), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (ROOT/'data/campus_manifest.json').write_text(json.dumps([item],indent=2),encoding='utf-8')
if __name__=='__main__':main()
