"""Student-facing decisions; existing proposal model screens remain available."""
from datetime import timedelta
from html import escape
import json
import math
import pandas as pd
import streamlit as st
from campus import runway,market_prices
from storage import wallet,save_wallet,commitments,add_commitment,pay_commitment,mission,ROOT
from vibes import reaction,hostel_desk
from delight import boarding_pass,group_chat,why_reaction,queue_celebration

def rupees(value):return f'Rs. {value:,.0f}'
def spend_limit(value):return rupees(math.floor(max(0,value)))

def wallet_editor(workspace,today,expanded=False):
    current=wallet(workspace)
    with st.expander('Set my allowance cycle',expanded=expanded or current is None):
        st.caption('Enter cash you actually have now, including cash and wallet balances. This replaces the previous snapshot; imported history is not subtracted again.')
        with st.form('wallet_setup'):
            a,b=st.columns(2)
            cash=a.number_input('Money I have right now (PKR)',min_value=0.0,value=max(0,float(current['cash'])) if current else 0.0,step=100.0)
            payday=b.date_input('Next allowance arrives',value=max(pd.Timestamp(current['payday']).date(),today+timedelta(days=1)) if current else today+timedelta(days=14),min_value=today+timedelta(days=1))
            a,b,c=st.columns(3)
            food=a.number_input('Minimum meals per day (PKR)',min_value=0.0,value=float(current['food_daily']) if current else 0.0,step=10.0)
            transport=b.number_input('Minimum transport per day (PKR)',min_value=0.0,value=float(current['transport_daily']) if current else 0.0,step=10.0)
            buffer=c.number_input('Emergency money to protect (PKR)',min_value=0.0,value=float(current['buffer']) if current else 0.0,step=100.0)
            complete=st.checkbox('My recent entries include all my spending, including no-spend days',value=bool(current['complete_history']) if current else False)
            if st.form_submit_button('Build my runway',type='primary'):
                from app.finance import operation_key
                nonce=st.session_state.get('wallet_snapshot_intent_'+workspace)
                request_id=operation_key('wallet-form',{'nonce':nonce,'cash':cash,'payday':payday,'buffer':buffer,'food':food,'transport':transport,'complete':complete,'today':today})[0] if nonce else None
                save_wallet(workspace,cash,payday,buffer,food,transport,complete,request_id=request_id)
                queue_celebration(workspace,'Allowance mapped. Your essentials have a plan.')
                st.rerun()
        if st.button('Start a new balance snapshot',key='new_snapshot_'+workspace):
            import uuid
            st.session_state['wallet_snapshot_intent_'+workspace]=uuid.uuid4().hex
            st.info('Review the current balance, then Build my runway. This starts a new snapshot even if its values match an earlier one.')
    return wallet(workspace)

def planner_header(state,profile,today):
    risk=state['essential_shortfall']>0 or state['runout'] is not None or state['shortfall']>0
    label='STRETCH MODE' if risk else 'YOU HAVE ROOM TO BREATHE'
    a,b,c,d=st.columns(4)
    a.metric('Wallet balance',rupees(profile['cash']))
    b.metric('Daily spending ceiling',spend_limit(state['daily_cap']))
    c.metric('Upcoming commitments',rupees(state['reserved']))
    d.metric('Days until allowance',str(state['days']))
    st.markdown(f'<div class="paper-summary">{label.title()} · Optional spending: <strong>{spend_limit(state["optional_cap"])}/day</strong> after daily essentials. Emergency reserve: <strong>{rupees(profile["buffer"])}</strong>.</div>',unsafe_allow_html=True)
    if state['essential_shortfall']>0:
        st.error(f"There is a {rupees(state['essential_shortfall'])} gap even before optional spending. Check the amounts or arrange additional funds; cutting social spending alone cannot cover your stated essentials.")
    elif state['runout']:
        st.warning(f"At your recorded pace, cash runs out around {state['runout'].strftime('%d %B')}. The daily ceiling above is the pace needed to reach your allowance date while keeping your reserve.")
    elif state['shortfall']>0:
        st.warning(f"Your current pace reaches allowance day but uses {rupees(state['shortfall'])} of your protected reserve.")
    else:st.success('Your entered plan covers essentials and commitments through allowance day.')
    reaction('tight' if state['essential_shortfall']>0 else 'pace' if risk else 'safe')

def render_runway(workspace,df,today):
    if workspace=='Household sample':
        st.info('Switch to My finances for the PKR allowance planner. The historical household reference stays in INR.')
        return
    st.markdown('<div class="section-kicker">HOSTEL LIFE. REAL PLANS. ONE ALLOWANCE.</div>',unsafe_allow_html=True)
    st.title('Wallet overview')
    st.write('Your allowance, spending and upcoming commitments in one place.')
    profile=wallet(workspace)
    if profile is None:profile=wallet_editor(workspace,today,expanded=True)
    if profile is None:
        reaction('empty')
        st.markdown('<div class="empty-wallet">◒<h3>Start with what is in your pocket.</h3><p>Add your cash, next allowance date and basic daily costs above. Your expenses can then update this plan automatically.</p></div>',unsafe_allow_html=True)
        return
    try:state=runway(profile,df,commitments(workspace),today)
    except ValueError as error:st.warning(str(error));return
    if profile.get('asof') and pd.Timestamp(profile['asof']).date()<today:
        st.warning(f"Cash was last updated on {profile['asof']}. Update the snapshot or log missing spending before relying on today's ceiling.")
    planner_header(state,profile,today)
    wallet_editor(workspace,today)
    from intelligence import render_insights
    render_insights(df,today)
    st.subheader('Your next move')
    left,right=st.columns([1.5,1])
    with left:
        st.markdown('**A pace you can actually follow**')
        choice=st.slider('Optional spending per day',0,500,min(500,int(state['optional_cap'])),step=5 if int(state['optional_cap'])%5==0 else 1,format='Rs. %d')
        chosen=runway(profile,df,commitments(workspace),today,daily_optional=choice)
        st.line_chart(chosen['timeline'].set_index('date'),color=['#ef796e','#8580ff','#c4b59a'])
        st.caption(f"Current pace: {rupees(state['rate'])}/day. Basis: {state['method']}. The purple line uses your meal/transport minimum plus the optional cap you chose. Dates are estimates, not guaranteed future balances.")
    with right:
        with st.container(border=True):
            st.markdown('### Protect first. Enjoy the rest.')
            st.write(f"🍽 Meals + transport: **{rupees(state['essential_daily'])}/day**")
            st.write(f"🛡 Emergency reserve: **{rupees(profile['buffer'])}**")
            st.write(f"🗓 Next allowance: **{pd.Timestamp(profile['payday']).strftime('%d %b')}**")
            if chosen['timeline']['Your chosen plan'].iloc[-1]>=profile['buffer']:
                st.success(f"This cap leaves {rupees(chosen['timeline']['Your chosen plan'].iloc[-1])} at allowance day.")
            else:st.warning(f"This cap misses your reserve by {rupees(profile['buffer']-chosen['timeline']['Your chosen plan'].iloc[-1])}.")
    st.subheader('Money with a job')
    st.caption('Reserve known costs once. Mark a cost paid only when you actually paid it; that records the expense and updates cash without reserving it twice.')
    pending=commitments(workspace)
    if not pending.empty:
        for row in pending.itertuples():
            a,b,c=st.columns([3,1,1])
            a.write(f"{'✓' if row.paid else '◷'} **{row.label}** · {row.due}")
            b.write(rupees(row.amount))
            if not row.paid and c.button('Record paid',key=f'paid_{workspace}_{row.id}'):
                pay_commitment(workspace,row.id,today);st.rerun()
    with st.expander('Reserve an upcoming fee, trip or essential'):
        with st.form('new_commitment'):
            label=st.text_input('What is the money for?',placeholder='Trip home / mess bill / project printing')
            a,b,c=st.columns(3)
            due=a.date_input('Due on',today+timedelta(days=3))
            amount=b.number_input('Reserve amount (PKR)',min_value=0.0,step=100.0)
            category=c.selectbox('Expense category',['Bills','Transport','Education','Health','Other'])
            if st.form_submit_button('Ring-fence this money'):
                try:add_commitment(workspace,label,due,amount,category);st.rerun()
                except ValueError as error:st.error(str(error))

def sync_price(source,target):
    st.session_state[target]=float(st.session_state[source])


def render_purchase(workspace,df,today):
    st.markdown('<div class="section-kicker">THE BEFORE-YOU-BUY BUTTON</div>',unsafe_allow_html=True)
    st.title('Can I say yes?')
    st.write('A weekend plan, a delivery, a new pair of earphones. See what it does to the rest of your allowance.')
    if workspace=='Household sample':st.info('Use My finances for PKR purchase decisions. The household reference is in INR.');return
    profile=wallet(workspace)
    if not profile:st.info('Set your allowance cycle on Allowance runway first.');return
    label=st.text_input('What is the plan?',value='Dinner with friends')
    num_key=f'purchase_number_{workspace}'
    slide_key=f'purchase_slider_{workspace}'
    for key in (num_key,slide_key):
        if key not in st.session_state:st.session_state[key]=350.0
    cost=st.number_input('What will it cost? (PKR)',min_value=0.0,step=50.0,key=num_key,on_change=sync_price,args=(num_key,slide_key))
    limit=float(math.ceil(max(2000,profile['cash']*1.2,cost)/500)*500)
    st.slider('Alternate timeline: slide the price',min_value=0.0,max_value=limit,step=1.0,key=slide_key,on_change=sync_price,args=(slide_key,num_key),format='Rs. %.0f')
    st.caption('Try a cheaper plan or a bigger splurge. This slider only changes the scenario.')
    try:
        base=runway(profile,df,commitments(workspace),today)
        after=runway(profile,df,commitments(workspace),today,purchase=cost)
    except ValueError as error:st.warning(str(error));return
    a,b=st.columns([1.3,1])
    with a:
        if base['essential_shortfall']>0:verdict='Fund the existing essentials first.'
        elif after['affordable']:verdict='There is room for this.'
        elif after['essential_shortfall']<=profile['buffer']:verdict='This uses your protected buffer.'
        else:verdict='This squeezes meals or commitments.'
        color='good' if after['affordable'] else 'tight'
        st.markdown(f'<div class="verdict verdict-chat {color}"><div class="hero-kicker">{escape(label.upper())}</div><h2>{verdict}</h2><p>{rupees(cost)} now leaves {rupees(profile["cash"]-cost)} in your wallet.</p></div>',unsafe_allow_html=True)
        if after['affordable']:
            st.write(f"After buying it, your daily ceiling becomes **{spend_limit(after['daily_cap'])}**, including meals and transport. It fits only if you follow that ceiling.")
        else:
            if base['essential_shortfall']>0:
                st.write(f"This cycle already has a **{rupees(base['essential_shortfall'])} gap** before the purchase. This plan adds {rupees(cost)}, taking the total gap to {rupees(after['essential_shortfall'])}.")
            elif after['essential_shortfall']<=profile['buffer']:
                st.write(f"Even with optional spending cut to zero, this uses **{rupees(after['essential_shortfall'])} of your protected emergency reserve**.")
            else:
                st.write(f"Even using the full emergency reserve, meals and commitments are **{rupees(after['essential_shortfall']-profile['buffer'])} short**.")
        st.write(f"Your maximum one-off spend after protecting all stated essentials is **{spend_limit(base['safe_purchase_max'])}**.")
    with b:
        st.metric('Daily ceiling before',spend_limit(base['daily_cap']))
        st.metric('Daily ceiling after',spend_limit(after['daily_cap']),delta=f"{after['daily_cap']-base['daily_cap']:.0f} per day",delta_color='inverse')
        if after['purchase_essential_days'] is not None:st.caption(f"That purchase equals {after['purchase_essential_days']:.1f} days of your entered meals and transport costs.")
    reaction('tight' if base['essential_shortfall']>0 else 'free' if cost==0 else 'affordable' if after['affordable'] else 'buffer' if after['essential_shortfall']<=profile['buffer'] else 'tight')
    group_chat(base,after,profile,cost,label)
    why_reaction(base,after,profile,cost)
    postpone=st.checkbox('Compare waiting until after my next allowance')
    scenario_cost=0 if postpone else cost
    baseline=runway(profile,df,commitments(workspace),today,daily_optional=base['optional_cap'])
    unchanged=runway(profile,df,commitments(workspace),today,purchase=scenario_cost,daily_optional=base['optional_cap'])
    adjusted=runway(profile,df,commitments(workspace),today,purchase=scenario_cost,daily_optional=base['optional_cap'] if postpone else after['optional_cap'])
    st.line_chart(pd.DataFrame({'Before purchase at daily ceiling':baseline['timeline']['Your chosen plan'].to_numpy(),
                                'Purchase without adjusting daily spending':unchanged['timeline']['Your chosen plan'].to_numpy(),
                                'Purchase with adjusted daily ceiling':adjusted['timeline']['Your chosen plan'].to_numpy(),
                                'Protected reserve':profile['buffer']},index=base['timeline'].date),color=['#a4a0c4','#ed8d78','#8580ff','#c4b59a'])
    if postpone:st.info('Waiting removes the purchase from this cycle. Affordability after the next allowance depends on that next cycle’s income and costs.')
    st.caption('This is a what-if calculation. It does not record a purchase or move money. Log the expense only after you actually spend it.')

def render_mission(workspace,df,today):
    st.markdown('<div class="section-kicker">A SMALL WIN WITH A REAL PAYOFF</div>',unsafe_allow_html=True)
    st.title('The weekend pass.')
    st.write('Give optional spending a boundary, so saying yes to friends does not mean borrowing for meals.')
    reaction('mission')
    if workspace=='Household sample':st.info('Use My finances for a PKR weekend pass.');return
    week=today-timedelta(days=today.weekday())
    saved=mission(workspace,week)
    with st.form('mission'):
        a,b=st.columns(2)
        category=a.selectbox('This week I am watching',['Entertainment','Shopping'],index=0 if not saved or saved['category']=='Entertainment' else 1)
        cap=b.number_input('My weekly cap (PKR)',min_value=1.0,value=float(saved['cap']) if saved else 500.0,step=50.0)
        if st.form_submit_button('Start my weekend pass',type='primary'):
            mission(workspace,week,category,cap)
            queue_celebration(workspace,'Weekend boundary set. Social plans, with the basics protected.')
            st.rerun()
    if saved:
        records=df[(df.kind=='Expense')&(df.category==saved['category'])&(df.date>=pd.Timestamp(week))&(df.date<=pd.Timestamp(today))]
        spent=float(records.amount.sum())
        st.markdown(f'<div class="pass-card"><div class="hero-kicker">WEEKEND PASS · {week.strftime("%d %b")}</div><h2>{rupees(max(0,saved["cap"]-spent))} left to enjoy</h2><p>{escape(saved["category"])} · {rupees(spent)} used of {rupees(saved["cap"])}</p></div>',unsafe_allow_html=True)
        st.progress(min(1,spent/saved['cap']))
        st.caption('Progress comes from logged expenses. This is a spending cap, not extra money: check your allowance runway before using it.')
        if spent>saved['cap']:st.warning(f"You are {rupees(spent-saved['cap'])} over this cap. Review the next plan before spending again.")
        else:st.success('Pass is on track. Meals and essential travel stay outside this optional-spending challenge.')

def render_prices(today):
    st.markdown('<div class="section-kicker">REAL PAKISTAN DATA, NOT GUESSED CAMPUS PRICES</div>',unsafe_allow_html=True)
    st.title('The grocery reality check.')
    st.write('For students buying groceries or sharing a kitchen: build a small ingredient basket using observed market prices.')
    reaction('prices')
    market=st.selectbox('Reference market',['Karachi','Lahore','Multan','Peshawar','Quetta'])
    prices=market_prices(market)
    if not prices.empty:prices=prices[prices.date<=pd.Timestamp(today)]
    if prices.empty:st.info('Download the WFP Pakistan price dataset to enable this screen.');return
    st.caption(f"Source: WFP via HDX · {len(prices):,} observed retail records for {market}. Sukkur is not covered by this dataset; these are reference prices, not campus or canteen quotes.")
    prices=prices[~prices.commodity.str.contains('Wage|Fuel',case=False,regex=True)]
    options=sorted(prices.commodity.unique())
    defaults=[c for c in options if 'Rice' in c or 'Lentil' in c][:2]
    selected=st.multiselect('Ingredients for my basket',options,default=defaults)
    basket=[]
    for commodity in selected:
        history=prices[prices.commodity==commodity]
        latest=history.iloc[-1]
        qty=st.number_input(f"{commodity} · quantity in {latest['unit']}",min_value=0.0,value=1.0,step=.5,key=f'qty_{market}_{commodity}')
        basket.append({'Item':commodity,'Unit':latest['unit'],'Quantity':qty,'Price (PKR)':float(latest.price),'Basket cost (PKR)':float(latest.price)*qty,'Observed on':latest.date.date()})
    if basket:
        st.dataframe(pd.DataFrame(basket),hide_index=True)
        st.metric('Reference basket cost',rupees(sum(r['Basket cost (PKR)'] for r in basket)))
        oldest=min(r['Observed on'] for r in basket)
        age=(today-oldest).days
        if age>60:st.warning(f'At least one selected price is {age} days old. Use the basket for historical context and enter current shop prices before making a real budget.')
    if selected:
        series=prices[prices.commodity.isin(selected)].pivot_table(index='date',columns='commodity',values='price',aggfunc='mean')
        st.line_chart(series.tail(24))
    st.link_button('Open the original WFP dataset','https://data.humdata.org/dataset/wfp-food-prices-for-pakistan')

def dataset_cards():
    path=ROOT/'data'/'campus_manifest.json'
    if not path.exists():return
    st.subheader('Data behind the student edition')
    for item in json.loads(path.read_text()):
        with st.expander(f"{item['name']} · {item['rows']:,} rows"):
            st.write(item['use'])
            st.caption(item['limits'])
            st.link_button('Original source',item['source'],key='source_'+item['file'])
            st.dataframe(pd.read_csv(ROOT/'data'/item['file']).head(10),hide_index=True)
