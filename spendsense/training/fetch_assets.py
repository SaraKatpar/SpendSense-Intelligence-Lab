"""Download public model/data assets to explicit project directories with resume.

Only data and safetensors are downloaded. No remote Python is executed.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import time
import requests

ROOT=Path(__file__).resolve().parents[1]

def download(url,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    partial=path.with_suffix(path.suffix+'.part')
    if path.exists():return
    for attempt in range(6):
        try:
            size=partial.stat().st_size if partial.exists() else 0
            with requests.get(url,headers={'Range':f'bytes={size}-'} if size else {},stream=True,timeout=(20,30)) as response:
                response.raise_for_status()
                append=size>0 and response.status_code==206
                with partial.open('ab' if append else 'wb') as handle:
                    for chunk in response.iter_content(256*1024):handle.write(chunk)
            partial.replace(path)
            print(f'Downloaded {path.name}',flush=True)
            return
        except requests.RequestException:
            if attempt==5:raise
            time.sleep(2)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',action='store_true');parser.add_argument('--receipts',action='store_true')
    args=parser.parse_args();jobs=[]
    if args.model:
        for name in ['config.json','tokenizer_config.json','tokenizer.json','vocab.txt','model.safetensors']:
            jobs.append((f'https://huggingface.co/distilbert/distilbert-base-uncased/resolve/main/{name}',ROOT/'models'/'base-distilbert'/name))
    if args.receipts:
        for index in range(5):
            stem=f'{index:03}'
            for remote,local,suffix in [('img','images','jpg'),('key','entities','json')]:
                jobs.append((f'https://raw.githubusercontent.com/zzzDavid/ICDAR-2019-SROIE/master/data/{remote}/{stem}.{suffix}',ROOT/'data'/'sroie'/local/f'{stem}.{suffix}'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(lambda job:download(*job),jobs):pass

if __name__=='__main__':main()
