"""Allowance runway: explicit cash accounting and explainable what-if plans."""
import math
import pandas as pd
from analytics import expenses
from storage import read,add,wallet,save_wallet,add_commitment,commitments,ROOT

def runway(profile,txns,obligations,today,purchase=0.0,daily_optional=0.0):
    if not math.isfinite(float(purchase)) or purchase<0 or not math.isfinite(float(daily_optional)) or daily_optional<0:
        raise ValueError('Scenario amounts must be finite and non-negative.')
    today=pd.Timestamp(today).normalize();payday=pd.Timestamp(profile['payday']).normalize()
    days=(payday-today).days
    if days<=0:raise ValueError('Set your next allowance date after today.')
    upcoming=obligations.loc[(obligations.paid==0)&(pd.to_datetime(obligations.due)<payday)].copy() if not obligations.empty else obligations.copy()
    reserved=float(upcoming.amount.sum()) if not upcoming.empty else 0
    essential=float(profile['food_daily']+profile['transport_daily'])
    cash=float(profile['cash'])
    total_cap=max(0,(cash-profile['buffer']-reserved-purchase)/days)
    optional_cap=max(0,total_cap-essential)
    recent=expenses(txns)
    recent=recent[(recent.date<today)&(recent.date>=today-pd.Timedelta(days=14))&(~recent.category.isin(['Bills','Education','Health']))&recent.source.ne('planned')]
    rate=essential
    method='Entered food + transport minimum'
    if profile['complete_history'] and len(recent)>=7:
        observed=min(14,max(1,(today-recent.date.min()).days))
        rate=max(essential,float(recent.amount.sum())/observed)
        method=f'Your recorded variable spending over {observed} completed days'
    balance=cash-purchase
    planned_balance=cash-purchase
    rows=[];runout=None
    for day in pd.date_range(today,payday-pd.Timedelta(days=1)):
        due=float(upcoming.loc[pd.to_datetime(upcoming.due).clip(lower=today).eq(day),'amount'].sum()) if not upcoming.empty else 0
        balance-=rate+due
        planned_balance-=essential+daily_optional+due
        rows.append({'date':day,'Current pace':balance,'Your chosen plan':planned_balance,'Emergency reserve':profile['buffer']})
        if balance<0 and runout is None:runout=day.date()
    deficit=max(0,essential*days+reserved+profile['buffer']+purchase-cash)
    return {'days':days,'cash':cash,'reserved':reserved,'essential_daily':essential,'daily_cap':total_cap,
            'optional_cap':optional_cap,'rate':rate,'method':method,'runout':runout,
            'shortfall':max(0,profile['buffer']-balance),'essential_shortfall':deficit,
            'end_balance':balance,'timeline':pd.DataFrame(rows),'commitments':upcoming,
            'purchase_essential_days':purchase/essential if essential>0 else None,
            'affordable':deficit<=0,'safe_purchase_max':max(0,cash-profile['buffer']-reserved-essential*days)}

def market_prices(market):
    path=ROOT/'data'/'wfp_food_prices_pak.csv'
    if not path.exists():return pd.DataFrame()
    data=pd.read_csv(path,low_memory=False)
    data=data[data.market.eq(market)&data.currency.eq('PKR')&data.pricetype.eq('Retail')&data.priceflag.eq('actual')].copy()
    data['date']=pd.to_datetime(data.date,errors='coerce')
    data['price']=pd.to_numeric(data.price,errors='coerce')
    return data.dropna(subset=['date','price']).sort_values('date')
