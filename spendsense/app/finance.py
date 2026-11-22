"""Single intake currency and money policy; no implicit exchange conversion.

Persist quantized compatibility REAL values; arithmetic uses integer minor units.
ROUND_HALF_UP applies once per amount before both ledger and cash adjustment.
"""
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CURRENCY_PATTERNS = {
    'USD': r'\bUSD\b|\$', 'INR': r'\bINR\b|₹', 'EUR': r'\bEUR\b|€',
    'GBP': r'\bGBP\b|£', 'MYR': r'\bMYR\b|\bRM\b', 'PKR': r'\bPKR\b',
    'AED': r'\bAED\b', 'SAR': r'\bSAR\b', 'CAD': r'\bCAD\b',
    'AUD': r'\bAUD\b', 'CNY': r'\bCNY\b|\bRMB\b|¥', 'JPY': r'\bJPY\b',
    'BDT': r'\bBDT\b|৳', 'NPR': r'\bNPR\b', 'CHF': r'\bCHF\b'}
# Codes often touch the amount (USD120, RM33.90); alphabetic boundaries allow
# digits without accidentally detecting a code inside a merchant's word.
CURRENCY_PATTERNS = {code: re.sub(r'\\b([A-Za-z]+)\\b', r'(?<![A-Za-z])\1(?![A-Za-z])', pattern)
                     for code, pattern in CURRENCY_PATTERNS.items()}


def currencies(text):
    return {code for code, pattern in CURRENCY_PATTERNS.items() if re.search(pattern, str(text), re.I)}


def currency_of(text):
    found = currencies(text)
    return next(iter(found)) if len(found) == 1 else 'MIXED' if found else None


def workspace_currency(workspace):
    return 'INR' if workspace == 'Household sample' else 'PKR'


def enforce_currency(workspace, currency=None, text=''):
    expected = workspace_currency(workspace)
    found = currencies(text)
    if currency is not None and str(currency).strip():
        found.add(str(currency).strip().upper())
    if found - {expected}:
        raise ValueError(f'Only {expected} is accepted in this workspace; detected {", ".join(sorted(found))}. No currency conversion is performed. Create a new manual entry with the verified local-currency amount.')
    return expected


def minor_units(value, positive=False, signed=False):
    if isinstance(value, bool):
        raise ValueError('Enter a finite numeric money amount.')
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or abs(amount) > Decimal('1000000000') or (not signed and amount < 0):
            raise ValueError('Money must be finite, nonnegative and at most 1,000,000,000.')
        units = int((amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, OverflowError):
        raise ValueError('Enter a valid numeric money amount.') from None
    if positive and units <= 0:
        raise ValueError('Amount must remain positive after rounding to two decimal places.')
    return units


def money(value, positive=False, signed=False):
    return minor_units(value, positive, signed) / 100


def change_cash(conn, workspace, delta, asof, revision=None):
    row = conn.execute('SELECT cash,revision FROM wallets WHERE workspace=?', (workspace,)).fetchone()
    if not row or (revision is not None and row[1] != revision):
        return False
    units = minor_units(row[0], signed=True) + minor_units(delta, signed=True)
    conn.execute('UPDATE wallets SET cash=?,asof=? WHERE workspace=?', (units / 100, str(asof), workspace))
    return True


def operation_key(operation, payload, request_id=None):
    encoded = json.dumps({'operation': operation, 'payload': payload}, sort_keys=True, default=str, allow_nan=False)
    return request_id or hashlib.sha256(encoded.encode()).hexdigest(), encoded


def replay(conn, workspace, operation, payload, request_id=None):
    token, encoded = operation_key(operation, payload, request_id)
    old = conn.execute('SELECT payload,result FROM intake_receipts WHERE workspace=? AND token=?', (workspace, token)).fetchone()
    if old:
        if old[0] != encoded:
            raise ValueError('This save token was already used for different data. Start a new entry.')
        return token, encoded, json.loads(old[1])
    return token, encoded, None


def receipt(conn, workspace, token, encoded, result):
    conn.execute('INSERT INTO intake_receipts VALUES(?,?,?,?)', (workspace, token, encoded, json.dumps(result)))
