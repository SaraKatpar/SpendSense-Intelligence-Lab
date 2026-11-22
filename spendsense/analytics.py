"""Deterministic evidence for the dashboard, recurrence detector and mystery."""
import re
import numpy as np
import pandas as pd

def expenses(df):
    return df.loc[df.kind.eq('Expense')].copy()

def weekly_mystery(df, today):
    """Compare two complete Mon–Sun weeks; never compare a partial week."""
    end = pd.Timestamp(today).normalize() - pd.Timedelta(days=pd.Timestamp(today).weekday())
    start = end - pd.Timedelta(days=7)
    previous = start - pd.Timedelta(days=7)
    x = expenses(df)
    a = x[(x.date >= start) & (x.date < end)]
    b = x[(x.date >= previous) & (x.date < start)]
    if len(a) < 3 or len(b) < 3:
        return None
    changes = a.groupby('category').amount.sum().subtract(b.groupby('category').amount.sum(), fill_value=0).sort_values(ascending=False)
    if changes.empty or changes.iloc[0] <= 0:
        return None
    suspect = changes.index[0]
    return {'answer': suspect, 'increase': float(changes.iloc[0]),
            'current': float(a[a.category.eq(suspect)].amount.sum()),
            'previous': float(b[b.category.eq(suspect)].amount.sum()),
            'count': int(a.category.eq(suspect).sum()),
            'start': start.date(), 'end': (end-pd.Timedelta(days=1)).date(),
            'options': sorted(set(a.category) | set(b.category))}

def recurring_payments(df):
    x = expenses(df)
    x['payee'] = x.merchant.fillna('').where(x.merchant.fillna('').str.strip().ne(''), x.description)
    x['payee'] = x.payee.str.lower().map(lambda s: re.sub(r'[^a-z0-9 ]','',s).strip())
    results = []
    for payee, rows in x.groupby('payee'):
        rows = rows.sort_values('date')
        if not payee or len(rows) < 3:
            continue
        gaps = rows.date.diff().dt.days.dropna()
        median = float(gaps.median())
        amount = float(rows.amount.median())
        # Require consistent cadence and amounts, rather than repeated names alone.
        if any(lo <= median <= hi for lo,hi in [(6,8),(13,15),(27,33)]) and (abs(gaps-median) <= 3).all() and (abs(rows.amount-amount) <= max(1,amount*.1)).all():
            results.append({'Merchant': payee.title(), 'Typical amount': amount,
                            'Interval (days)': round(median), 'Occurrences': len(rows),
                            'Next estimated': (rows.date.max()+pd.Timedelta(days=round(median))).date()})
    return results

def behavior_features(df, reference=None):
    x = expenses(df)
    if x.empty:
        return np.zeros(5, dtype=np.float32)
    if reference is not None:
        x = x[x.date.le(pd.Timestamp(reference)) & x.date.ge(pd.Timestamp(reference)-pd.Timedelta(days=29))]
    total = x.amount.sum()
    if total <= 0:
        return np.zeros(5, dtype=np.float32)
    return np.array([x[x.date.dt.weekday>=5].amount.sum()/total,
                     x[x.category.eq('Entertainment')].amount.sum()/total,
                     x[x.category.eq('Food')].amount.sum()/total,
                     x[x.category.eq('Shopping')].amount.sum()/total,
                     min(len(x)/30, 5)/5], dtype=np.float32)
