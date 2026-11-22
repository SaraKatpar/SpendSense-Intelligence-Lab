"""Daily survival projections: learned optional spending + explicit protected costs."""
import pandas as pd
from campus import runway
from storage import commitments,wallet
import ml
import streamlit as st

OPTIONAL=['Entertainment','Shopping','Other']


def hybrid_daily_costs(essential_daily,dates,obligations,optional_costs):
    """Shared projection composition, independent of any opening cash balance."""
    import math
    dates=pd.DatetimeIndex(dates)
    values=list(optional_costs)
    if not len(dates) or len(values)!=len(dates):raise ValueError('Forecast dates and costs must align.')
    if not math.isfinite(float(essential_daily)) or essential_daily<0 or any(not math.isfinite(float(v)) or v<0 for v in values):raise ValueError('Projection costs must be finite and nonnegative.')
    due=pd.Series(0.,index=dates)
    if not obligations.empty:
        unpaid=obligations.loc[obligations.paid.eq(0)].copy()
        unpaid['effective_due']=pd.to_datetime(unpaid.due).clip(lower=dates[0])
        for day,amount in unpaid.groupby('effective_due').amount.sum().items():
            if day in due.index:due.loc[day]+=float(amount)
    return pd.Series([essential_daily+float(v) for v in values],index=dates)+due

def scenario(profile,df,obligations,today,purchase=0,delay=0,optional_reduction=0):
    if delay<0 or not 0<=optional_reduction<=100:raise ValueError('Invalid scenario change.')
    changed=dict(profile);changed['payday']=(pd.Timestamp(profile['payday'])+pd.Timedelta(days=delay)).date().isoformat()
    base=runway(changed,df,obligations,today,purchase=purchase)
    optional=max(0,base['rate']-base['essential_daily'])*(1-optional_reduction/100)
    plan=runway(changed,df,obligations,today,purchase=purchase,daily_optional=optional)
    return base,plan


def projected_balances(profile,obligations,today,optional_costs):
    state=runway(profile,pd.DataFrame(columns=['kind','date','category','source','amount']),obligations,today)
    dates=state['timeline'].date
    if len(optional_costs)!=len(dates):raise ValueError('Prediction length differs from allowance horizon.')
    return profile['cash']-hybrid_daily_costs(state['essential_daily'],dates,state['commitments'],optional_costs).cumsum()


def render_survival(workspace,df,today):
    st.title('Survival forecast')
    profile=wallet(workspace)
    if workspace=='Household sample' or not profile:st.info('Set your balance, next allowance and daily essentials in Financial HQ first.');return
    obligations=commitments(workspace)
    try:state=runway(profile,df,obligations,today)
    except ValueError as error:st.warning(str(error));return
    a,b,c=st.columns(3)
    a.metric('Protected daily ceiling',f"Rs. {int(state['daily_cap']):,}")
    b.metric('Discretionary ceiling',f"Rs. {int(state['optional_cap']):,}")
    c.metric('Current-pace allowance balance',f"Rs. {state['end_balance']:,.0f}")
    st.caption('These are financial calculations. Current pace: '+state['method']+'. Daily ceilings protect commitments and emergency money.')
    st.line_chart(state['timeline'].set_index('date'))
    if state['runout']:st.warning(f"Current recorded pace exhausts cash around {state['runout']:%d %b}. This is an estimate, not a probability.")
    st.subheader('Learned forecast vs a statistical baseline')
    if not profile['complete_history']:
        st.info('Confirm that your recent history is complete in allowance settings before using learned projections. The essential-cost calculation above is the transparent fallback.');return
    if state['days']>365:st.info('Learned forecasts are limited to 365 days. Use a nearer allowance date.');return
    prediction=ml.forecast_days(df,today,state['days'])
    if prediction is None:
        st.info('No suitable trained model or fewer than 14 calendar days of history. No learned prediction is shown. Train a personal model from the documented pipeline; reference INR models are never substituted into a PKR account.');return
    # Keep reserves explicit; never add forecast fixed-category totals to known commitments.
    optional=[c for c in OPTIONAL if c not in set(state['commitments'].category)]
    learned=prediction[optional].sum(axis=1)
    recent=ml.daily_matrix(df,pd.Timestamp(today)-pd.Timedelta(days=1)).tail(7)
    baseline=float(recent[optional].sum(axis=1).mean()) if len(recent) else 0
    a,b=st.columns(2)
    a.metric('LSTM scenario daily spending',f"Rs. {state['essential_daily']+learned.mean():,.0f}")
    b.metric('Baseline daily spending',f"Rs. {state['essential_daily']+baseline:,.0f}")
    learned_balance=projected_balances(profile,obligations,today,learned.to_numpy())
    baseline_balance=projected_balances(profile,obligations,today,[baseline]*state['days'])
    chart=pd.DataFrame({'LSTM + protected costs':learned_balance,'7-day mean + protected costs':baseline_balance,'Emergency reserve':profile['buffer']})
    st.line_chart(chart,color=['#45d6a5','#7189cb','#d9b761'])
    a,b=st.columns(2)
    a.metric('LSTM projected final balance',f"Rs. {learned_balance.iloc[-1]:,.0f}")
    b.metric('Baseline projected final balance',f"Rs. {baseline_balance.iloc[-1]:,.0f}")
    exhausted=learned_balance[learned_balance<0]
    if len(exhausted):st.warning(f"The learned scenario exhausts cash around {exhausted.index[0]:%d %b}.")
    elif learned_balance.iloc[-1]<profile['buffer']:st.warning('The learned scenario uses part of the protected reserve.')
    else:st.success('The learned scenario stays above your entered reserve through allowance day.')
    st.caption('LSTM predicts Shopping, Entertainment and Other spending only here, excluding categories with reserved commitments. Entered meals/transport and dated commitments are added once. Other unreserved essential costs must be entered in Financial HQ. This is a scoped forecast, not a full probability model.')
    info=ml.metadata('forecast')
    if info:st.caption('Model provenance: '+str(info.get('data'))+' · '+str(info.get('caution','')))
    st.dataframe(prediction,hide_index=False)


def render_scenarios(workspace,df,today):
    profile=wallet(workspace)
    if not profile or workspace=='Household sample':return
    st.subheader('Allowance delay & spending changes')
    st.caption('What-if only: these controls do not edit your balance or your allowance date. Essentials stay protected.')
    a,b=st.columns(2)
    delay=a.slider('Allowance arrives late (days)',0,14,0)
    reduction=b.slider('Reduce discretionary pace (%)',0,100,0,step=5)
    purchase=st.number_input('Additional scenario purchase (PKR)',min_value=0.,value=0.,step=100.)
    try:
        before,original=scenario(profile,df,commitments(workspace),today)
        after,changed=scenario(profile,df,commitments(workspace),today,purchase,delay,reduction)
    except ValueError as error:st.warning(str(error));return
    a,b,c=st.columns(3)
    a.metric('Scenario days',after['days'],delta=delay)
    b.metric('Safe daily ceiling',f"Rs. {int(after['daily_cap']):,}",delta=f"{after['daily_cap']-before['daily_cap']:.0f}")
    final=float(changed['timeline']['Your chosen plan'].iloc[-1])
    c.metric('Scenario final balance',f'Rs. {final:,.0f}')
    frame=pd.concat([original['timeline'].set_index('date')['Your chosen plan'].rename('Original pace'),changed['timeline'].set_index('date')['Your chosen plan'].rename('Changed pace')],axis=1)
    st.line_chart(frame)
    st.caption('Comparison uses recorded variable-spending pace only when history coverage is confirmed; otherwise it uses entered essentials. The original line ends at the original allowance date; it is not extended with fabricated future income.')
    if final<profile['buffer']:st.warning(f"This scenario misses your protected reserve by Rs. {profile['buffer']-final:,.0f}.")

    if profile['complete_history'] and after['days']<=365:
        prediction=ml.forecast_days(df,today,after['days'])
        if prediction is not None:
            before_cols=[c for c in OPTIONAL if c not in set(before['commitments'].category)]
            after_cols=[c for c in OPTIONAL if c not in set(after['commitments'].category)]
            prior_ml=projected_balances(profile,commitments(workspace),today,prediction[before_cols].sum(axis=1).iloc[:before['days']].to_numpy())
            changed_profile=dict(profile,cash=profile['cash']-purchase,payday=(pd.Timestamp(profile['payday'])+pd.Timedelta(days=delay)).date().isoformat())
            after_ml=projected_balances(changed_profile,commitments(workspace),today,(prediction[after_cols].sum(axis=1)*(1-reduction/100)).to_numpy())
            st.markdown('**Same scenario through the LSTM pipeline**')
            st.line_chart(pd.concat([prior_ml.rename('Original LSTM scenario'),after_ml.rename('Changed LSTM scenario')],axis=1))
            st.caption('Learned optional categories plus explicit protected costs, as in Survival forecast. Purchase is deducted once. The reduction applies to predicted discretionary costs, not meals or transport.')
