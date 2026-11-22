"""Frozen monthly target-measurement rules. No estimator or fitted transform.

Raw monetary values are used to check ledger arithmetic, never exported as
model features. Every model input/target scale is a dimensionless ratio.
"""
from collections import Counter,defaultdict
import numpy as np

EVENT_RATIO=0.05
HISTORY_MONTHS=12
BASELINE_MONTHS=3
MIN_BASELINE_DEBITS=3
MIN_HISTORY_MEAN_DEBITS=4
MIN_ACTIVE_FRACTION=0.8
MIN_TARGET_OBSERVATION_DATES=2
PARTITIONS={'train':('1993-01-01','1996-12-31'),
            'validation':('1997-01-01','1997-12-31'),
            'test':('1998-01-01','1998-12-31')}


def closing_balance(group):
    """Exact closing snapshot if uniquely identified, else retain bounds.

    Each post-transaction balance and signed amount implies a before->after
    ledger edge. A connected directed Euler trail with unique terminal vertex
    determines the closing balance without assuming file/trans_id ordering.
    Inconsistent/disconnected/cyclic graphs are never patched or averaged.
    """
    after=np.rint(group.balance.to_numpy()*100).astype('int64')
    amounts=np.rint(group.amount.to_numpy()*100).astype('int64')
    known=group.type.isin(['PRIJEM','VYDAJ','VYBER']).all()
    low=int(after.min());high=int(after.max())
    if low==high:
        return {'status':'single_or_equal_snapshot','point_czk':low/100,'lower_czk':low/100,'upper_czk':high/100}
    if not known:
        return {'status':'unknown_direction','point_czk':None,'lower_czk':low/100,'upper_czk':high/100}
    signs=np.where(group.type.eq('PRIJEM').to_numpy(),1,-1)
    before=after-amounts*signs
    incoming=Counter(after);outgoing=Counter(before);vertices=set(incoming)|set(outgoing)
    starts=[x for x in vertices if outgoing[x]-incoming[x]==1]
    ends=[x for x in vertices if incoming[x]-outgoing[x]==1]
    if len(starts)!=1 or len(ends)!=1 or any(abs(outgoing[x]-incoming[x])>1 for x in vertices):
        return {'status':'unresolved_degree','point_czk':None,'lower_czk':low/100,'upper_czk':high/100}
    adjacency=defaultdict(set)
    for first,last in zip(before,after):adjacency[first].add(last);adjacency[last].add(first)
    stack=[starts[0]];seen=set()
    while stack:
        node=stack.pop()
        if node in seen:continue
        seen.add(node);stack.extend(adjacency[node]-seen)
    if seen!=vertices:
        return {'status':'unresolved_disconnected','point_czk':None,'lower_czk':low/100,'upper_czk':high/100}
    return {'status':'unique_ledger_terminal','point_czk':int(ends[0])/100,'lower_czk':low/100,'upper_czk':high/100}
