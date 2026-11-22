
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="SpendSense | Intelligence Lab",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp {
    background: #080f21;
    color: #f5f3ff;
}
[data-testid="stSidebar"] {
    background: #0c1429;
    border-right: 1px solid #26304a;
}
[data-testid="stSidebar"] * {
    color: #d9d4ef;
}
.block-container {
    padding-top: 2rem;
    max-width: 1500px;
}
.hero {
    background: linear-gradient(120deg, #141c38, #1c1640);
    border: 1px solid #34305a;
    border-radius: 22px;
    padding: 30px;
    min-height: 230px;
    box-shadow: 0 0 30px #8b5cf615;
}
.card {
    background: #111a32;
    border: 1px solid #293453;
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 14px;
}
.small-label {
    color: #a5a8c0;
    font-size: 13px;
}
.big-number {
    color: #ffffff;
    font-size: 32px;
    font-weight: 750;
}
.accent {
    color: #b88cff;
}
div[data-testid="stMetric"] {
    background: #111a32;
    border: 1px solid #293453;
    padding: 16px;
    border-radius: 16px;
}
.stButton > button {
    background: #35235d;
    color: white;
    border: 1px solid #6246a3;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ✳ SpendSense.")
    st.caption("YOUR FINANCIAL INTELLIGENCE LAB")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "🏠 Intelligence HQ",
            "📸 Capture Studio",
            "📈 Future Lab",
            "🧬 Spending DNA",
            "🔍 Pattern Detective",
            "🧪 Model Arena",
        ],
        label_visibility="collapsed"
    )

    st.divider()
    st.caption("STUDENT MODE + ML LAB")
    st.caption("SpendSense v2.0")

if page == "🏠 Intelligence HQ":

    st.caption("SPENDSENSE / INTELLIGENCE HQ")
    st.title("Your money, decoded. ✨")

    left, right = st.columns([1.65, 1], gap="large")

    with left:
        st.markdown("""
        <div class="hero">
            <div class="small-label">YOUR PERSONAL INTELLIGENCE HQ</div>
            <h2>Hey, future financial genius! 👾</h2>
            <p>Let's investigate your spending patterns,
            predict what happens next, and make sense
            of your money.</p>
            <h3 class="accent">✦ Your financial universe awaits.</h3>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("Spending Breakdown")

        sample = pd.DataFrame({
            "Category": ["Food", "Transport", "Shopping", "Bills", "Other"],
            "Amount": [3200, 1200, 2400, 900, 600]
        })

        st.bar_chart(sample.set_index("Category"))

    with right:
        st.markdown("""
        <div class="card">
            <div class="small-label">FINANCIAL INTELLIGENCE</div>
            <h2>🧠 Spending Health</h2>
            <p>Analyze your financial behavior with machine learning.</p>
            <span class="accent">Explore your insights →</span>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("Quick Overview")
        a, b = st.columns(2)
        a.metric("Available Balance", "Rs. 6,250")
        b.metric("Monthly Spending", "Rs. 3,750")

        st.markdown("""
        <div class="card">
            <h3>🧬 Spending DNA</h3>
            <p>Discover your unique spending patterns.</p>
            <span class="accent">ML analysis coming soon</span>
        </div>
        """, unsafe_allow_html=True)

elif page == "📸 Capture Studio":
    st.title("📸 Capture Studio")
    st.write("Turn receipts and descriptions into organized expenses.")

    description = st.text_input("Describe your expense")
    amount = st.number_input("Amount (Rs.)", min_value=0.0)

    if st.button("Analyze Expense"):
        if description and amount > 0:
            st.info("Expense captured. ML categorization will be connected next.")
        else:
            st.warning("Enter a description and amount.")

elif page == "📈 Future Lab":
    st.title("📈 Future Lab")
    st.write("Predict future spending using historical patterns.")
    st.info("LSTM model integration is pending.")

elif page == "🧬 Spending DNA":
    st.title("🧬 Spending DNA")
    st.write("Explore spending behavior through K-Means clustering.")
    st.info("Clustering integration is pending.")

elif page == "🔍 Pattern Detective":
    st.title("🔍 Pattern Detective")
    st.write("Investigate unusual transactions.")
    st.info("Autoencoder integration is pending.")

elif page == "🧪 Model Arena":
    st.title("🧪 Model Arena")
    st.write("Compare and evaluate machine learning models.")
    st.info("Evaluation dashboard integration is pending.")

