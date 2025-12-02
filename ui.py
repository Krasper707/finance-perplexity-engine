import streamlit as st
import requests
import json

# --- CONFIG ---
API_URL = "http://localhost:8000/analyze"
st.set_page_config(page_title="Mini-Perplexity Finance", layout="wide")

# --- CUSTOM CSS (To make it look pro) ---
st.markdown("""
<style>
    .source-card {
        background-color: #1E1E1E;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 3px solid #00D4FF;
    }
    .metric-box {
        background-color: #0E1117;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #262730;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🔎 Financial Engine")
    st.markdown("---")
    st.write("This engine uses **AsyncIO** to scrape news and **Pandas** to calculate RSI in real-time.")
    
    # History Placeholder
    if "history" not in st.session_state:
        st.session_state.history = []
    
    if st.session_state.history:
        st.subheader("Recent Searches")
        for tick in st.session_state.history:
            st.caption(f"• {tick}")

# --- MAIN PAGE ---
st.title("💸 AI Financial Analyst")
st.caption("Enter a stock ticker (e.g., AAPL, TSLA, NVDA) to generate a cited research report.")

ticker_input = st.text_input("Ticker Symbol", placeholder="AAPL").upper()

if st.button("Generate Report", type="primary"):
    if not ticker_input:
        st.warning("Please enter a ticker.")
    else:
        # Add to history
        if ticker_input not in st.session_state.history:
            st.session_state.history.append(ticker_input)

        # 1. SHOW LOADING STATE
        with st.status("🚀 Engine Running...", expanded=True) as status:
            st.write("1. 📡 Connecting to Market Data (yfinance)...")
            st.write("2. 🕷️ Scraping News Sources (Tavily)...")
            st.write("3. 🧠 Synthesizing Report (LLM)...")
            
            # 2. CALL THE API
            try:
                payload = {"ticker": ticker_input}
                response = requests.post(API_URL, json=payload)
                data = response.json()
                
                status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Failed to connect to backend. Is server.py running? {e}")
                st.stop()

        # 3. DISPLAY RESULTS
        # We use columns to separate the Report from the Sources (Perplexity Style)
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"Analysis for {data.get('ticker', ticker_input)}")
            # Render the Markdown Report
            st.markdown(data['report'])
            
            # Show Latency Metric
            st.info(f"⏱️ Computation Time: {data.get('time_taken', 'N/A')}")

        with col2:
            st.subheader("📚 Sources")
            sources = data.get('sources', [])
            if sources:
                for s in sources:
                    st.markdown(f"""
                    <div class="source-card">
                        <b>[{s['id']}] {s['title']}</b><br>
                        <a href="{s['url']}" target="_blank" style="color: #00D4FF; text-decoration: none;">Read Source 🔗</a>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write("No news sources found.")