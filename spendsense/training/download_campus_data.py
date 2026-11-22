"""Re-fetch the four public Campus datasets; validate before replacing files."""
from pathlib import Path
from io import BytesIO
import zipfile
import requests
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]/'data'

def save_csv(name,payload,required):
    frame=pd.read_csv(BytesIO(payload))
    if not set(required).issubset(frame.columns):raise ValueError(f'{name}: unexpected source format')
    path=ROOT/name;temporary=path.with_suffix('.csv.tmp')
    temporary.write_bytes(payload);temporary.replace(path)
    print(f'{name}: {len(frame):,} rows',flush=True)

def get(url):
    response=requests.get(url,timeout=(20,60));response.raise_for_status()
    if len(response.content)>15_000_000:raise ValueError('Unexpectedly large dataset response.')
    return response.content

def main():
    ROOT.mkdir(exist_ok=True)
    save_csv('wfp_food_prices_pak.csv',get('https://data.humdata.org/dataset/125455ff-c8a8-4f4b-9190-bf0e84559dc7/resource/8cf7a8a2-58a1-4c3f-bafe-f38af68d971b/download/wfp_food_prices_pak.csv'),['date','market','commodity','unit','price','currency'])

if __name__=='__main__':main()
