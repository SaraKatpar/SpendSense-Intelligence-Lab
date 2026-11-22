"""Read-only export of CTU's Financial database; no cleaning or training.

Run: python training/fetch_berka.py --output data/berka_raw
The default login is the public guest login published by CTU, not a private key.
"""
import argparse
import csv
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path
import pymysql

TABLES=('account','order','trans')


def export(output):
    output.mkdir(parents=True,exist_ok=True)
    connection=pymysql.connect(host='relational.fel.cvut.cz',port=3306,user='guest',
        password=os.environ.get('BERKA_DB_PASSWORD','ctu-relational'),database='financial',
        connect_timeout=15,read_timeout=90,charset='utf8mb4',autocommit=False)
    manifest={'source':'https://relational.fel.cvut.cz/dataset/Financial','database':'financial',
        'version':'CTU Financial (MariaDB), not the unmodified original ASC archive',
        'real_data_evidence':'CTU dataset page labels Type: Real; account units are accounts, not necessarily individual people or students.',
        'downloaded_utc':datetime.now(timezone.utc).isoformat(),'sql_null_encoding':'\\N',
        'transformations':'Only CSV serialization; no row filtering, imputation, category mapping or amount conversion.',
        'redistribution':'Public access does not itself establish a redistribution license. Verify terms before bundling exports publicly.',
        'complete':False,'tables':{}}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SET SESSION TRANSACTION READ ONLY')
            connection.begin()
            # Discover the schema before exporting any values.
            for table in TABLES:
                cursor.execute('DESCRIBE `'+table+'`')
                schema=[dict(zip(('name','sql_type','nullable','key','default','extra'),row)) for row in cursor.fetchall()]
                cursor.execute('SELECT COUNT(*) FROM `'+table+'`');count=cursor.fetchone()[0]
                manifest['tables'][table]={'schema':schema,'expected_rows':count}
                print(table,'columns:',[col['name'] for col in schema],'rows:',count,flush=True)
        for table in TABLES:
            path=output/(table+'.csv');partial=output/(table+'.csv.part');count=0
            with connection.cursor() as cursor,partial.open('w',newline='',encoding='utf-8') as handle:
                key=manifest['tables'][table]['schema'][0]['name'];last_id=-1
                writer=csv.writer(handle);writer.writerow([col['name'] for col in manifest['tables'][table]['schema']])
                while True:
                    # Keyset batches stay below the public server's statement timeout.
                    cursor.execute('SELECT * FROM `'+table+'` WHERE `'+key+'` > %s ORDER BY `'+key+'` LIMIT 10000',(last_id,))
                    rows=cursor.fetchall()
                    if not rows:break
                    writer.writerows([['\\N' if value is None else value for value in row] for row in rows]);count+=len(rows)
                    last_id=rows[-1][0]
                    if count%200000==0:print(table,count,'rows exported',flush=True)
            if count!=manifest['tables'][table]['expected_rows']:raise RuntimeError('Row-count mismatch for '+table)
            partial.replace(path)
            manifest['tables'][table].update({'rows':count,'file':path.name,'bytes':path.stat().st_size,
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            print('Verified export:',table,count,flush=True)
            (output/'provenance.json').write_text(json.dumps(manifest,indent=2,default=str),encoding='utf-8')
        manifest['complete']=True
        (output/'provenance.json').write_text(json.dumps(manifest,indent=2,default=str),encoding='utf-8')
    finally:connection.close()
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=Path('data/berka_raw'))
    args=parser.parse_args();export(args.output)
