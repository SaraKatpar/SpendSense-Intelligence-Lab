"""Per-user reviewed corrections, layered over a shared global categorizer.

Exact reviewed descriptions use their most recent correction. Otherwise a fixed
0.85 character-TF-IDF similarity gate permits a same-label nearest correction;
ties across labels abstain. No feedback crosses workspace boundaries.
"""
import re
import unicodedata
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

SIMILARITY_THRESHOLD=.85


def normalize(text):
    text=unicodedata.normalize('NFKC',str(text)).casefold()
    return ' '.join(re.findall(r'\w+',text,flags=re.UNICODE))


def initialize(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS category_corrections(
        id INTEGER PRIMARY KEY,workspace TEXT NOT NULL,description TEXT NOT NULL,
        normalized TEXT NOT NULL,category TEXT NOT NULL,created_at TEXT NOT NULL,
        transaction_id INTEGER)''')


def learn(conn,workspace,description,category,created_at,transaction_id=None):
    initialize(conn)
    normalized=normalize(description)
    if not normalized:raise ValueError('A correction needs a description.')
    conn.execute('INSERT INTO category_corrections(workspace,description,normalized,category,created_at,transaction_id) VALUES(?,?,?,?,?,?)',
        (workspace,str(description),normalized,category,str(created_at),transaction_id))


def corrected_prediction(text,global_result,corrections):
    latest={normalize(row['description']):row['category'] for row in corrections if normalize(row['description'])}
    query=normalize(text)
    if not query or not latest:return global_result
    if query in latest:return latest[query],1.
    descriptions=list(latest)
    try:
        vectorizer=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),lowercase=False)
        matrix=vectorizer.fit_transform(descriptions)
        similarity=(matrix@vectorizer.transform([query]).T).toarray().ravel()
    except ValueError:return global_result
    best=float(similarity.max())
    labels={latest[descriptions[i]] for i in np.flatnonzero(np.isclose(similarity,best,rtol=0,atol=1e-12))}
    if best>=SIMILARITY_THRESHOLD and len(labels)==1:return next(iter(labels)),best
    return global_result


def predict(workspace,text,global_result):
    import storage
    with storage.connect() as conn:
        initialize(conn)
        rows=conn.execute('SELECT description,category FROM category_corrections WHERE workspace=? ORDER BY id',(workspace,)).fetchall()
    return corrected_prediction(text,global_result,[{'description':r[0],'category':r[1]} for r in rows])
