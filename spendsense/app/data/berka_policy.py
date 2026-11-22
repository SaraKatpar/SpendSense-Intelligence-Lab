"""User-approved Berka row eligibility. Never changes the original ASC files.

This selects operation eligibility only, not debit/credit direction. Later
spending features must additionally use documented transaction directions.
All amounts remain CZK; this module never imports them into a PKR wallet.
"""

UNKNOWN_ROLE='bank_generated/unknown_operation'


def label_rows(frame):
    if 'operation' not in frame.columns:raise ValueError('Berka operation column is required.')
    labeled=frame.copy()
    missing=labeled['operation'].fillna('').astype(str).str.strip().eq('')
    labeled['record_role']='observed_operation'
    labeled.loc[missing,'record_role']=UNKNOWN_ROLE
    return labeled


def rows_for(frame,purpose):
    """Retain all cash-flow/balance rows; exclude unknown operations for ML."""
    if purpose not in ('cash_flow','balance','spending','anomaly','persona'):
        raise ValueError('Choose cash_flow, balance, spending, anomaly or persona.')
    labeled=label_rows(frame)
    if purpose in ('spending','anomaly','persona'):
        return labeled.loc[labeled['record_role'].ne(UNKNOWN_ROLE)].copy()
    return labeled
