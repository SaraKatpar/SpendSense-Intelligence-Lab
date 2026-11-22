"""Compare full source statistics and 24 deterministic matched-ID examples.

This is not a full row-by-row MariaDB diff. No training/cleaning is performed.
"""
import argparse
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pymysql


def compare(path):
    original=pd.read_csv(path,sep=';',keep_default_na=False,usecols=['trans_id','type','amount','balance'])
    identifiers=[]
    for kind in original.type.unique():
        for column in ('amount','balance'):
            identifiers.extend(original.loc[original.type.eq(kind)&original[column].mod(1).ne(0),'trans_id'].head(6).astype(int).tolist())
    identifiers=list(dict.fromkeys(identifiers))
    conn=pymysql.connect(host='relational.fel.cvut.cz',user='guest',password=os.environ.get('BERKA_DB_PASSWORD','ctu-relational'),
        database='financial',connect_timeout=15,read_timeout=60,cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cursor:
            cursor.execute('SET SESSION TRANSACTION READ ONLY')
            cursor.execute('SELECT trans_id,amount,balance FROM trans WHERE trans_id IN ('+','.join(['%s']*len(identifiers))+')',identifiers)
            sample=cursor.fetchall()
            cursor.execute('SELECT COUNT(*) AS rows_count,SUM(amount) AS amount_sum,SUM(balance) AS balance_sum,SUM(amount=0) AS zero_amounts FROM trans')
            totals=cursor.fetchone()
    finally:conn.close()
    lookup=original.set_index('trans_id');examples=[]
    for row in sample:
        source=lookup.loc[row['trans_id']];item={'trans_id':row['trans_id']}
        for column in ('amount','balance'):
            item['original_'+column]=float(source[column]);item['sql_'+column]=row[column]
            item[column+'_difference_sql_minus_original']=round(row[column]-float(source[column]),2)
        examples.append(item)
    # Original monetary fields have hundredths; integer cents avoid sum drift.
    sums={column:format(int(np.rint(original[column].to_numpy()*100).astype(np.int64).sum())/100,'.2f') for column in ('amount','balance')}
    return {'comparison_scope':'Full-table source precision/counts/aggregate totals and a deterministic matched-ID sample, not a full row-by-row MariaDB diff.',
        'original':{'rows':len(original),'fractional_amount_rows':int(original.amount.mod(1).ne(0).sum()),
            'fractional_balance_rows':int(original.balance.mod(1).ne(0).sum()),'zero_amount_rows':int(original.amount.eq(0).sum()),
            'amount_sum':sums['amount'],'balance_sum':sums['balance']},
        'mariadb':{'amount_type':'int(11)','balance_type':'int(11)',**{key:str(value) for key,value in totals.items()}},
        'sample_rows':len(examples),'sample':examples,
        'source_decision':'Use the original archived ASC files: fractional amounts/balances are preserved. MariaDB is comparison/fallback only.',
        'currency':'CZK only. Never use raw monetary features in cross-currency models or import Berka into the PKR wallet.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trans',type=Path,default=Path('data/berka_original/trans.asc'))
    parser.add_argument('--output',type=Path,default=Path('eval/berka_precision_comparison.json'))
    args=parser.parse_args();result=compare(args.trans);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
