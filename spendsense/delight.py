"""Playful views derived from recorded facts. No LLM, payment or external assets."""
from html import escape
import math
import pandas as pd
import streamlit as st

def cash(value):return f'Rs. {value:,.0f}'
def ceiling(value):return cash(math.floor(max(0,value)))

def wallet_mood(state):
    if state['essential_shortfall']>0:return 'worried','essentials first','One thing at a time. Let’s cover the basics.'
    if state['runout'] is not None or state['shortfall']>0:return 'thinking','doing the maths','A smaller daily pace keeps the plot on track.'
    return 'calm','we have a plan','The essentials have a seat. So do your plans.'

def creature_html(state):
    mood,label,copy=wallet_mood(state)
    return f'''<div class="buddy-wrap"><div class="wallet-buddy {mood}" role="img" aria-label="Wallet buddy: {escape(label)}">
        <span class="buddy-tuft" aria-hidden="true">✦</span><span class="buddy-eye left" aria-hidden="true"></span>
        <span class="buddy-eye right" aria-hidden="true"></span><span class="buddy-mouth" aria-hidden="true"></span>
        <span class="buddy-cheek left" aria-hidden="true"></span><span class="buddy-cheek right" aria-hidden="true"></span></div>
        <strong>{escape(label)}</strong><p>{escape(copy)}</p></div>'''

def boarding_pass(state,profile,today):
    payday=pd.Timestamp(profile['payday'])
    st.markdown(f'''<section class="boarding-ticket" aria-label="Allowance boarding pass"><div class="ticket-main">
        <div class="ticket-eyebrow">SPENDSENSE AIR ✦ ADMIT ONE HUMAN WITH PLANS</div>
        <div class="ticket-route"><span>{today.strftime('%d %b').upper()}</span><b aria-hidden="true">↗</b><span>{payday.strftime('%d %b').upper()}</span></div>
        <p>NOW → ALLOWANCE DAY · {state['days']} DAYS TO GO</p><div class="ticket-stats">
        <div><small>IN YOUR WALLET</small><strong>{cash(profile['cash'])}</strong></div>
        <div><small>COMMITMENTS</small><strong>{cash(state['reserved'])}</strong></div>
        <div><small>OPTIONAL / DAY</small><strong>{ceiling(state['optional_cap'])}</strong></div></div>
        <div class="ticket-barcode" aria-hidden="true"></div><small>YOUR BUDGET IS THE BOARDING PASS. NO ACTUAL TRAVEL BOOKING.</small>
        </div><div class="ticket-stub">{creature_html(state)}</div></section>''',unsafe_allow_html=True)

def purchase_messages(base,after,profile,cost,label):
    if base['essential_shortfall']>0:
        wallet=f"The existing plan is already {cash(base['essential_shortfall'])} short. This adds {cash(cost)}, bringing the gap to {cash(after['essential_shortfall'])}."
    elif cost==0:wallet=f"Free plans? Elite. Your daily ceiling stays {ceiling(base['daily_cap'])}."
    elif after['affordable']:wallet=f"This fits if the daily ceiling drops from {ceiling(base['daily_cap'])} to {ceiling(after['daily_cap'])}."
    elif after['essential_shortfall']<=profile['buffer']:wallet=f"Even with optional spending at zero, this uses {cash(after['essential_shortfall'])} of the emergency reserve."
    else:wallet=f"Even using the full reserve, meals and commitments would be {cash(after['essential_shortfall']-profile['buffer'])} short."
    future=(f"Keep the {cash(profile['buffer'])} reserve and follow the new daily ceiling. A little treat can have a plan."
            if after['affordable'] else f"There is {ceiling(base['safe_purchase_max'])} for a one-off purchase after the stated essentials are protected. We can change the plan, not pretend there is extra cash.")
    return [('You',f'Can we do {label or "this plan"} for {cash(cost)}?'),('Wallet',wallet),('Future You',future)]

def group_chat(base,after,profile,cost,label):
    icons={'You':'🙂','Wallet':'🫧','Future You':'🌱'}
    bubbles=''.join(f'<div class="chat-message {"outgoing" if name=="You" else "incoming"}"><span class="chat-icon" aria-hidden="true">{icons[name]}</span><div><small>{name.upper()}</small><p>{escape(text)}</p></div></div>' for name,text in purchase_messages(base,after,profile,cost,label))
    st.markdown(f'<section class="wallet-chat" aria-label="Budget group chat"><div class="chat-heading">THE GROUP CHAT <span>3 participants · all of them are you</span></div>{bubbles}</section>',unsafe_allow_html=True)
    st.caption('Scripted explanations of your budget calculation—not messages from other people or a generative AI chat.')

def why_reaction(base,after,profile,cost):
    needs=base['essential_daily']*base['days']
    rows=[('Cash entered',cash(profile['cash'])),('What-if purchase',cash(cost)),('Remaining meals + transport',cash(needs)),
          ('Unpaid commitments before allowance',cash(base['reserved'])),('Protected reserve',cash(profile['buffer'])),
          ('Protected-money gap after purchase',cash(after['essential_shortfall']))]
    body=''.join(f'<div><span>{escape(name)}</span><strong>{value}</strong></div>' for name,value in rows)
    st.markdown(f'<details class="reaction-receipts"><summary>↻ Why this reaction? Show the receipts.</summary><div class="reason-back">{body}<p>Daily ceiling = max(0, (cash − purchase − commitments − reserve) ÷ days left). The buddy is reacting to those numbers, not judging you.</p></div></details>',unsafe_allow_html=True)

def queue_celebration(workspace,message):st.session_state['planning_win']={'workspace':workspace,'message':message}

def show_celebration(workspace):
    win=st.session_state.pop('planning_win',None)
    if not win or win['workspace']!=workspace:return
    sparks=''.join(f'<i style="--spark:{i}" aria-hidden="true">✦</i>' for i in range(7))
    st.markdown(f'<div class="planning-win" role="status"><strong>✦ SMALL WIN, REAL PLAN.</strong><span>{escape(win["message"])}</span>{sparks}</div>',unsafe_allow_html=True)

def receipt_polaroids(df,currency='PKR'):
    records=df[df.source.eq('receipt')].sort_values(['date','id'],ascending=False).head(9)
    if records.empty:return
    st.subheader('The receipt wall')
    st.caption('Tap a card for the details. These are saved transaction summaries, not stored copies of your receipt photographs.')
    cards=[]
    for row in records.itertuples():
        merchant=str(row.merchant or 'Receipt entry')
        cards.append(f'''<details class="receipt-polaroid"><summary><div class="polaroid-paper"><small>SPENDSENSE / RECEIPT #{row.id}</small>
            <strong>{escape(merchant)}</strong><span class="paper-rule"></span><b>{currency} {row.amount:,.2f}</b>
            <em>{escape(row.category.upper())}</em><small>{row.date.strftime('%d %b %Y')} · TAP TO FLIP ↻</small></div></summary>
            <div class="polaroid-back"><strong>The details</strong><p>{escape(str(row.description))}</p><p>{escape(row.kind)} · {escape(row.category)}</p><small>Recorded from a reviewed receipt. This card does not verify the original merchant or payment.</small></div></details>''')
    st.markdown('<div class="receipt-wall">'+''.join(cards)+'</div>',unsafe_allow_html=True)

def delight_styles():
    moving=st.session_state.get('floating_stickers',True)
    st.markdown('''<style>
.boarding-ticket{display:flex;border:2px solid var(--ink);border-radius:18px;background:#fffdf8;box-shadow:5px 5px 0 var(--lilac);margin:12px 6px 25px 0;overflow:hidden;color:var(--ink)}
.ticket-main{flex:1;padding:22px 24px;min-width:0}.ticket-eyebrow{font-size:9px;font-weight:850;letter-spacing:1.4px}.ticket-route{display:flex;gap:20px;align-items:center;font-family:'Arial Black',sans-serif;font-size:30px;letter-spacing:-1px;margin-top:8px}.ticket-route b{font-size:35px;color:#8060be}.ticket-main>p{font-size:9px;letter-spacing:1px;color:#777079}.ticket-stats{display:flex;gap:24px;flex-wrap:wrap;margin:14px 0}.ticket-stats div{display:flex;flex-direction:column;gap:4px}.ticket-stats small{font-size:8px;letter-spacing:1px}.ticket-stats strong{font-size:20px;letter-spacing:-.5px}.ticket-main>small{font-size:7px;letter-spacing:.5px;color:#706972}.ticket-barcode{height:19px;width:140px;background:repeating-linear-gradient(90deg,#242424 0 2px,transparent 2px 4px,#242424 4px 5px,transparent 5px 9px);margin:10px 0 6px}.ticket-stub{width:185px;border-left:2px dashed #b8acc5;background:var(--lilac);display:grid;place-items:center;padding:16px}
.buddy-wrap{text-align:center}.buddy-wrap>strong{display:block;font-size:12px;letter-spacing:-.2px;margin-top:8px}.buddy-wrap>p{font-size:10px;color:#4e4657;line-height:1.4;max-width:145px;margin:4px auto 0}.wallet-buddy{position:relative;margin:9px auto;width:90px;height:82px;background:var(--lime);border:2px solid #242424;border-radius:45% 48% 39% 40%;box-shadow:3px 4px 0 #242424;animation:buddy-bob 4s ease-in-out infinite}.buddy-tuft{position:absolute;top:-23px;left:29px;font-size:31px;color:#5f449a}.buddy-eye{position:absolute;top:28px;width:9px;height:12px;background:#242424;border-radius:50%}.buddy-eye.left{left:23px}.buddy-eye.right{right:23px}.buddy-mouth{position:absolute;top:48px;left:34px;width:20px;height:10px;border-bottom:2px solid #242424;border-radius:0 0 50% 50%}.buddy-cheek{position:absolute;top:44px;width:12px;height:5px;background:#f99a96;border-radius:50%;opacity:.8}.buddy-cheek.left{left:12px}.buddy-cheek.right{right:12px}.thinking .buddy-eye.right{height:3px;top:33px;border-radius:2px;transform:rotate(-12deg)}.thinking .buddy-mouth{height:2px;top:51px;left:35px;width:16px;border-radius:0;transform:rotate(-7deg)}.worried{background:#ffd39d}.worried .buddy-mouth{border-bottom:0;border-top:2px solid #242424;border-radius:50% 50% 0 0;top:48px}.worried .buddy-eye.left{transform:rotate(15deg)}.worried .buddy-eye.right{transform:rotate(-15deg)}
.wallet-chat{border:2px solid var(--ink);border-radius:16px;background:#fffdf8;padding:17px;margin:12px 0;box-shadow:4px 4px 0 var(--lilac)}.chat-heading{font-size:10px;font-weight:850;letter-spacing:1px;border-bottom:1px solid #e2dce8;padding-bottom:12px}.chat-heading span{display:block;font-size:9px;font-weight:400;letter-spacing:0;color:#756c79;margin-top:4px}.chat-message{display:flex;gap:9px;margin:14px 0;max-width:94%;align-items:flex-start}.chat-message.outgoing{margin-left:auto;flex-direction:row-reverse}.chat-icon{font-size:22px;min-width:24px}.chat-message>div{border:1px solid #28252d;border-radius:12px 12px 12px 3px;padding:10px 12px;background:#eee6fc}.chat-message.outgoing>div{background:var(--lime);border-radius:12px 12px 3px 12px}.chat-message small{font-size:8px;letter-spacing:1px;font-weight:800;color:#6b5b7c}.chat-message p{margin:4px 0 0;font-size:12px;line-height:1.55}.verdict-chat{padding:17px!important;box-shadow:3px 3px 0 var(--ink)!important;margin-bottom:17px!important}.verdict-chat h2{font-size:25px!important;margin:8px 0!important}.timeline-chip{font-size:11px;font-weight:700;display:inline-block;padding:7px 11px;background:var(--lilac);border:1.5px solid var(--ink);border-radius:25px;margin:7px 0 12px}
.reaction-receipts{border:1.5px solid var(--ink);border-radius:12px;background:#fffdf8;margin:10px 0 22px;overflow:hidden}.reaction-receipts summary{cursor:pointer;font-weight:750;font-size:12px;padding:13px;list-style:none}.reaction-receipts summary:focus-visible,.receipt-polaroid summary:focus-visible{outline:3px solid #9270de;outline-offset:3px}.reason-back{padding:5px 15px 15px;animation:flip-in .2s ease-out}.reason-back>div{display:flex;justify-content:space-between;gap:12px;font-size:12px;padding:7px 0;border-bottom:1px dashed #d9cfe6}.reason-back p{font-size:11px;line-height:1.6;color:#6b6370;margin-top:13px}
.receipt-wall{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px;padding:10px 9px 26px}.receipt-polaroid{background:#fffdf8;border:1.5px solid #28252d;box-shadow:5px 6px 0 #d0c4e4;padding:12px 12px 23px;transform:rotate(-2deg);transition:transform .2s ease;align-self:start}.receipt-polaroid:nth-child(even){transform:rotate(2deg)}.receipt-polaroid:hover,.receipt-polaroid[open]{transform:rotate(0) translateY(-3px)}.receipt-polaroid summary{list-style:none;cursor:pointer}.polaroid-paper{display:flex;flex-direction:column;align-items:center;gap:11px;background:#f4eee3;padding:19px 10px;font-family:Consolas,monospace;text-align:center;word-break:break-word}.polaroid-paper small{font-size:8px;color:#72685e}.polaroid-paper>strong{font-size:15px;text-transform:uppercase}.paper-rule{width:100%;border-bottom:1px dashed #9d8f7d}.polaroid-paper b{font-size:22px;letter-spacing:-1px}.polaroid-paper em{font-size:10px;font-weight:800;font-style:normal;padding:4px 7px;background:var(--lime);border:1px solid #242424;transform:rotate(-6deg)}.polaroid-back{padding:14px 2px 0;animation:flip-in .2s ease-out}.polaroid-back p{font-size:12px;overflow-wrap:anywhere}.polaroid-back small{font-size:10px;color:#736b78}
.planning-win{position:relative;overflow:hidden;border:2px solid var(--ink);background:var(--lime);padding:17px 20px;border-radius:15px;box-shadow:4px 4px 0 var(--ink);margin-bottom:22px}.planning-win>strong,.planning-win>span{display:block}.planning-win>strong{font-size:11px;letter-spacing:1px}.planning-win>span{font-size:13px;margin-top:6px}.planning-win i{position:absolute;right:calc(10px + var(--spark)*22px);top:0;color:#8958c4;animation:win-spark 1.3s ease-out both;animation-delay:calc(var(--spark)*.07s);font-style:normal;pointer-events:none}
@keyframes buddy-bob{0%,100%{transform:translateY(0) rotate(-3deg)}50%{transform:translateY(-5px) rotate(3deg)}}@keyframes flip-in{from{opacity:0;transform:rotateX(-7deg)}to{opacity:1;transform:rotateX(0)}}@keyframes win-spark{0%{transform:translateY(45px) rotate(0);opacity:0}30%{opacity:1}100%{transform:translateY(-20px) rotate(110deg);opacity:0}}
@media(max-width:750px){.ticket-main{padding:17px 14px}.ticket-stub{width:108px;padding:10px 7px}.ticket-route{font-size:21px;gap:10px}.ticket-stats{gap:12px}.ticket-stats strong{font-size:16px}.ticket-eyebrow{font-size:7px}.buddy-wrap>p{display:none}.wallet-buddy{width:70px;height:67px}.buddy-eye{top:23px}.buddy-eye.left{left:17px}.buddy-eye.right{right:17px}.buddy-mouth{left:26px;top:40px;width:17px}.thinking .buddy-eye.right{top:28px}.thinking .buddy-mouth{left:27px;top:43px}.worried .buddy-mouth{top:40px}.buddy-tuft{left:22px}.buddy-cheek{top:36px}.receipt-wall{grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.polaroid-paper b{font-size:17px}.chat-heading span{max-width:230px}}
@media(max-width:420px){.receipt-wall{grid-template-columns:1fr}.boarding-ticket{display:block}.ticket-stub{width:auto;border-left:0;border-top:2px dashed #b8acc5}.buddy-wrap{display:flex;align-items:center;gap:18px}.buddy-wrap>strong{max-width:120px}.wallet-buddy{margin:12px 0 0}.ticket-main>small{font-size:6px}}
@media(prefers-reduced-motion:reduce){.wallet-buddy,.planning-win i,.reason-back,.polaroid-back{animation:none!important}}
</style>''',unsafe_allow_html=True)
    if not moving:st.markdown('<style>.wallet-buddy,.planning-win i,.reason-back,.polaroid-back{animation:none!important}.planning-win i{display:none}</style>',unsafe_allow_html=True)
