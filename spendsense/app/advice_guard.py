"""Authoritative numerical advice; model prose never overrides a failed check.

For checked purchase questions, return deterministic text instead of appending a
warning to potentially contradictory LLM text. No keyword blacklist is used on
the LLM response. Context must come from the server's accounting calculations.
"""
import re
from decimal import Decimal, ROUND_FLOOR, InvalidOperation
from app.finance import currencies,minor_units

PURCHASE = re.compile(r'\b(afford\w*|buy\w*|purchas\w*|cart|checkout|spend\w*|fit\w*|treat|splurge|say yes|can i|could i)\b',re.I)
AMOUNT = re.compile(r'(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w.])')


def check_purchase(context, amount, label='Purchase'):
    try:
        state=context.get('runway',{})
        ceiling=Decimal(str(state['safe_purchase_max']))
        shortfall=Decimal(str(state['essential_shortfall']))
        if not ceiling.is_finite() or ceiling<0 or not shortfall.is_finite() or shortfall<0:
            raise ValueError('Invalid numerical context.')
        cost=minor_units(amount,positive=True)
        maximum=int((ceiling*100).quantize(Decimal('1'),rounding=ROUND_FLOOR))
        affordable=shortfall==0 and cost<=maximum
        return {'status':'pass' if affordable else 'fail','label':label,'cost_minor':cost,
                'ceiling_minor':maximum,'gap_minor':max(0,cost-maximum),
                'essential_shortfall_minor':int((shortfall*100).to_integral_value(rounding='ROUND_CEILING'))}
    except (KeyError,ValueError,InvalidOperation,TypeError):
        return {'status':'unavailable','label':label}


def format_check(result):
    if result['status']=='unavailable':
        return 'I cannot verify whether this purchase fits. Set a valid current balance, next allowance date, daily essentials, reserve and upcoming dues, then give one PKR purchase total. No purchase is approved.'
    price=result['cost_minor']/100; maximum=result['ceiling_minor']/100
    # Do not echo untrusted cart labels or user instructions into a financial verdict.
    if result['status']=='fail':
        extra=(f" Your existing essentials plan is short by PKR {result['essential_shortfall_minor']/100:,.2f}."
               if result['essential_shortfall_minor'] else '')
        return (f'This purchase does not fit your protected plan. Price: PKR {price:,.2f}; '
                f'maximum after essentials, commitments and reserve: PKR {maximum:,.2f}. '
                f'The purchase exceeds that maximum by PKR {result["gap_minor"]/100:,.2f}.'+extra+
                ' Postpone it, reduce its price or add verified funds. Protected essentials and the reserve are not spare spending money.')
    return (f'The PKR {price:,.2f} purchase fits within the calculated protected maximum of PKR {maximum:,.2f}, '
            'using your entered balance, costs and dues. This is conditional on those records being complete and correct; nothing has been saved or deducted.')


def guarded_answer(history,context):
    """Return authoritative text or None if no numerical verdict is involved."""
    latest=next((str(m.get('content','')) for m in reversed(history) if m.get('role')=='user'),'')
    purchase=bool(PURCHASE.search(latest))
    if purchase:
        if currencies(latest)-{'PKR'}:
            return 'This PKR workspace cannot check a foreign-currency purchase. No conversion or purchase approval was made. Enter the verified PKR total separately.'
        without_dates=re.sub(r'\b\d{4}-\d{2}-\d{2}\b','',latest)
        amounts=[m.group().replace(',','') for m in AMOUNT.finditer(without_dates)]
        if len(amounts)==1:
            return format_check(check_purchase(context,amounts[0]))
        if len(amounts)>1:
            return 'I need one final PKR purchase total to check this safely. Multiple numbers could mean quantities, prices or installments; no purchase is approved.'
    # Any known failed cart check vetoes free-form model prose, even if a prompt
    # requests an exception or hides the financial question in unrelated wording.
    carts=context.get('planned_carts',[])
    checks=[check_purchase(context,c.get('amount'),str(c.get('label','Cart'))) for c in carts]
    failed=next((c for c in checks if c['status']=='fail'),None)
    if failed:return format_check(failed)
    # A follow-up such as "just say yes" must not bypass a failed numeric
    # question merely by omitting its price. Recheck prior user prices against
    # the current server-calculated plan. A new explicit price above is handled
    # first, so a genuinely changed scenario gets its own fresh calculation.
    for message in reversed(history[:-1]):
        previous=str(message.get('content',''))
        if message.get('role')!='user' or not PURCHASE.search(previous):continue
        previous=re.sub(r'\b\d{4}-\d{2}-\d{2}\b','',previous)
        amounts=[m.group().replace(',','') for m in AMOUNT.finditer(previous)]
        if len(amounts)==1 and not (currencies(previous)-{'PKR'}):
            prior=check_purchase(context,amounts[0])
            if prior['status']=='fail':return format_check(prior)
    state=context.get('runway',{})
    try:
        if Decimal(str(state.get('essential_shortfall',0)))>0:
            return ('Your entered essentials and commitments already exceed available funds. '
                    'A discretionary purchase cannot be approved. Verify your costs and balance or arrange additional funds; do not treat protected essentials as spare cash.')
    except InvalidOperation:
        if purchase:return format_check({'status':'unavailable'})
    if purchase:
        if len(checks)==1:return format_check(checks[0])
        return 'Give one final PKR purchase total and identify which cart you mean. I cannot approve an unspecified purchase.'
    return None
