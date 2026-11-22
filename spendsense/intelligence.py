"""Verified descriptive insights, kept separate from model decisions."""
import pandas as pd
import streamlit as st


def weekly_changes(df,today):
    end=pd.Timestamp(today).normalize();start=end-pd.Timedelta(days=7)
    expenses=df[(df.kind=='Expense')&(df.date<end)&(df.date>=start-pd.Timedelta(days=7))]
    current=expenses[expenses.date>=start].groupby('category').amount.sum()
    prior=expenses[expenses.date<start].groupby('category').amount.sum()
    frame=pd.DataFrame({'Previous 7 days':prior,'Latest 7 completed days':current}).fillna(0)
    frame['Change']=frame.iloc[:,1]-frame.iloc[:,0]
    return frame


def render_insights(df,today):
    st.subheader('What your records are saying')
    change=weekly_changes(df,today)
    if change.empty:st.caption('Log expenses to build a spending picture.');return
    largest=change.Change.idxmax()
    if change.loc[largest,'Change']>0:
        st.write(f"{largest} increased by Rs. {change.loc[largest,'Change']:,.0f} across the latest two completed seven-day periods.")
    st.bar_chart(change.iloc[:,:2])
    st.caption('Descriptive calculations from logged entries, not ML predictions. Missing entries can look like no spending; no causal or population claims are made.')


def explain_anomalies(df,result):
    st.caption('Model flags: autoencoder reconstruction error exceeds its stored validation threshold. Explanations below are separate descriptive comparisons, not proof of why the neural network flagged an entry.')
    for row in result.head(8).itertuples():
        prior=df[(df.kind=='Expense')&(df.category==row.category)&(df.date<row.date)]
        with st.expander(f"{row.category} · {row.date:%d %b} · Rs. {row.amount:,.0f}"):
            if len(prior)>=3:
                median=float(prior.amount.median())
                st.write(f"Earlier logged {row.category.lower()} purchases have median Rs. {median:,.0f} across {len(prior)} entries. This purchase is Rs. {row.amount-median:+,.0f} different.")
            else:st.write('Not enough earlier entries in this category for a reliable descriptive comparison.')
            previous=df[(df.kind=='Expense')&(df.category==row.category)&(df.date>=row.date-pd.Timedelta(days=7))&(df.date<row.date)]
            st.caption(f'{len(previous)} other matching-category expenses were recorded in the preceding seven days. A large legitimate purchase can be unusual without being irresponsible.')


def explain_style(df,today,shares):
    dominant=shares.idxmax()
    st.write(f"The largest recorded share is {dominant.lower()} at {shares.max():.1%} over the last 30 days. The cluster name is derived from its relative category shares, not your psychology.")
    rows=df[(df.kind=='Expense')&(df.date<=pd.Timestamp(today))&(df.date>=pd.Timestamp(today)-pd.Timedelta(days=59))].copy()
    rows['Period']=rows.date.apply(lambda x:'Latest 30 days' if x>=pd.Timestamp(today)-pd.Timedelta(days=29) else 'Previous 30 days')
    totals=rows.pivot_table(index='category',columns='Period',values='amount',aggfunc='sum',fill_value=0)
    st.bar_chart(totals)
    st.caption('Recorded totals, not proof of a stable trait. Different logging coverage can explain changes between periods.')
    if dominant in ['Meals','Social','Shopping & extras']:st.write('Try one realistic weekly limit for this category, then check the matched purchases in Spending coach.')
    else:st.write('Reserve upcoming travel and study costs before planning optional purchases. Your category mix is descriptive; it does not establish affordability.')
