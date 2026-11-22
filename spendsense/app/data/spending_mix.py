"""Shared, currency-free six-month spending timing/concentration features.

No category mapping is assumed: Berka has no food/merchant categories. Profiles
describe recorded debits, including bank fees/loan payments, not consumption or
student identities. This module does not load or deploy a model.
"""
import math
import numpy as np
import pandas as pd

FEATURES = ['days_01_10_share', 'days_11_20_share', 'days_21_end_share',
            'weekend_share', 'largest_20pct_transactions_share', 'transaction_hhi']


def profile(rows, start, end, observed_first, observed_last):
    """Return None unless six full observed-span months, 20 debits, 80% active.

    `rows` must already contain eligible, positive debits only, with date/amount.
    Coverage denotes observed span, never verified complete capture of spending.
    """
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    months = pd.period_range(start, end, freq='M')
    if (len(months) != 6 or start != months[0].start_time or
            end.normalize() != months[-1].end_time.normalize()):
        raise ValueError('A profile requires exactly six complete calendar months.')
    if pd.Timestamp(observed_first) > start or pd.Timestamp(observed_last) < end:
        return None
    selected = rows.loc[rows.date.between(start, end)].copy()
    if len(selected) < 20 or selected.date.dt.to_period('M').nunique() / 6 < .8:
        return None
    amount = selected.amount.to_numpy(dtype=np.float64)
    if not np.isfinite(amount).all() or (amount <= 0).any():
        raise ValueError('Eligible debits must have positive finite amounts.')
    shares = amount / amount.sum()
    dom = selected.date.dt.day.to_numpy()
    values = [shares[dom <= 10].sum(), shares[(dom > 10) & (dom <= 20)].sum(),
              shares[dom > 20].sum(), shares[selected.date.dt.dayofweek.to_numpy() >= 5].sum(),
              np.sort(shares)[-math.ceil(.2 * len(shares)):].sum(), (shares ** 2).sum()]
    return dict(zip(FEATURES, map(float, values))) | {
        'debit_rows': len(selected), 'active_months': selected.date.dt.to_period('M').nunique()}
