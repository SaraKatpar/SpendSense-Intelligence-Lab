"""Download/verify the pinned original archive and extract three unchanged ASC files."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import requests

URL='https://web.archive.org/web/20070214120527id_/http://lisp.vse.cz/pkdd99/DATA/data_berka.zip'
SHA256='affa4477572e9d8f2de6beff8a525d37c056d5d8e4a9670dd8c7636208c002ce'
SIZE=18074591


def fetch(archive,output):
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():
        partial=archive.with_suffix('.zip.part');offset=partial.stat().st_size if partial.exists() else 0
        headers={'Accept-Encoding':'identity'}
        if offset:headers['Range']=f'bytes={offset}-'
        with requests.get(URL,headers=headers,stream=True,timeout=(15,60)) as response:
            response.raise_for_status()
            if offset and (response.status_code!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {offset}-')):
                raise RuntimeError('Server did not honor resume. Keep the partial outside training and retry explicitly.')
            with partial.open('ab' if offset else 'wb') as handle:
                for chunk in response.iter_content(262144):handle.write(chunk)
        if partial.stat().st_size!=SIZE:raise RuntimeError('Archive is incomplete; no tables were extracted.')
        if hashlib.sha256(partial.read_bytes()).hexdigest()!=SHA256:raise RuntimeError('Archive checksum mismatch.')
        partial.replace(archive)
    if archive.stat().st_size!=SIZE or hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise RuntimeError('Pinned original archive checksum mismatch.')
    files={};output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip():raise RuntimeError('Archive CRC failure.')
        for name in ('account.asc','order.asc','trans.asc'):
            data=bundle.read(name);(output/name).write_bytes(data)
            files[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    manifest={'source':URL,'archive_bytes':SIZE,'archive_sha256':SHA256,'archive_crc_verified':True,
        'transformations':'Selected original ASC bytes extracted unchanged','currency':'CZK (user confirmed)',
        'training_source':'Original archive selected after precision comparison with MariaDB','files':files}
    (output/'provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Verified original files:',', '.join(files))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,default=Path('data/downloads/data_berka.zip'))
    parser.add_argument('--output',type=Path,default=Path('data/berka_original'))
    args=parser.parse_args();fetch(args.archive,args.output)
