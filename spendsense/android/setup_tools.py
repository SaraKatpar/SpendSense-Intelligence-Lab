"""Complete official SDK archives with range validation and published checksums.

Keeps tool downloads on E:. Reuses prior parts but trusts them only after the
complete archive matches Google's freshly fetched repository metadata.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import hashlib,json,math,time,zipfile,xml.etree.ElementTree as ET
import requests

TOOLS=Path('E:/extra curricular/SpendSense-build/android-tools').resolve()
BASE='https://dl.google.com/android/repository/'
CHUNK=262144


def fetch_part(url,start,end,total,dest):
    for attempt in range(4):
        try:
            with requests.get(BASE+url,headers={'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'},timeout=(10,20),stream=True) as response:
                response.raise_for_status()
                if response.status_code!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{total}':
                    raise ValueError('Range response mismatch: '+str(response.headers.get('Content-Range')))
                data=response.raw.read(decode_content=False)
                if len(data)!=end-start+1:raise ValueError('Incorrect range size.')
            dest.write_bytes(data);return
        except (requests.RequestException,ValueError):
            if attempt==3:raise
            time.sleep(.5*(attempt+1))


def package(name,spec,prefix,folder):
    size=int(spec.findtext('size'));digest=spec.findtext('checksum');url=spec.findtext('url')
    archive=TOOLS/url;parts=TOOLS/(prefix+'-complete-parts');parts.mkdir(exist_ok=True)
    count=math.ceil(size/CHUNK)
    for i in range(count):
        dest=parts/str(i);expected=min(CHUNK,size-i*CHUNK)
        if dest.exists() and dest.stat().st_size==expected:continue
        small=TOOLS/(prefix+'-small-parts')/str(i)
        if small.exists() and small.stat().st_size==expected:dest.write_bytes(small.read_bytes());continue
        large=TOOLS/(prefix+'-parts')/str(i//4)
        if large.exists():
            data=large.read_bytes()[(i%4)*CHUNK:(i%4)*CHUNK+expected]
            if len(data)==expected:dest.write_bytes(data)
    for full_refresh in (False,True):
        missing=[i for i in range(count) if full_refresh or not (parts/str(i)).exists() or (parts/str(i)).stat().st_size!=min(CHUNK,size-i*CHUNK)]
        print(name,'fetching',len(missing),'range parts',flush=True)
        with ThreadPoolExecutor(max_workers=6) as pool:
            jobs=[pool.submit(fetch_part,url,i*CHUNK,min(size-1,(i+1)*CHUNK-1),size,parts/str(i)) for i in missing]
            for n,future in enumerate(as_completed(jobs),1):
                future.result()
                if n%25==0:print(name,'downloaded',n,'/',len(jobs),flush=True)
        temporary=archive.with_suffix('.verified.tmp')
        with temporary.open('wb') as out:
            for i in range(count):out.write((parts/str(i)).read_bytes())
        if temporary.stat().st_size==size and hashlib.sha1(temporary.read_bytes()).hexdigest()==digest:
            temporary.replace(archive);break
        if full_refresh:raise ValueError('Published SDK checksum mismatch after complete fresh download.')
        print('Cached parts failed complete checksum; refreshing every range.',flush=True)
    target=(TOOLS/folder).resolve();assert target.is_relative_to(TOOLS)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip():raise ValueError('SDK CRC failure.')
        for entry in bundle.infolist():
            if not (target/entry.filename).resolve().is_relative_to(target):raise ValueError('SDK archive path traversal.')
        bundle.extractall(target)
    return {'package':name,'url':BASE+url,'bytes':size,'published_sha1':digest,
            'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'zip_crc':'passed','extracted_to':str(target)}


def main():
    TOOLS.mkdir(parents=True,exist_ok=True)
    response=requests.get(BASE+'repository2-3.xml',timeout=(15,30));response.raise_for_status()
    (TOOLS/'repository_current.xml').write_bytes(response.content)
    entries={p.attrib.get('path'):p for p in ET.fromstring(response.content) if p.tag.endswith('remotePackage')}
    results=[]
    for name,prefix,folder in [('build-tools;35.0.0','build-tools','build-tools'),('platforms;android-35','platform','platform')]:
        spec=next(a.find('complete') for a in entries[name].findall('./archives/archive') if a.findtext('host-os') in (None,'windows'))
        results.append(package(name,spec,prefix,folder))
    proof={'repository_url':BASE+'repository2-3.xml','repository_sha256':hashlib.sha256(response.content).hexdigest(),'packages':results}
    (TOOLS/'sdk_verified.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('Official SDK archives complete and verified.',flush=True)


if __name__=='__main__':main()
