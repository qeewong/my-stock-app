import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 頁面配置 ---
st.set_page_config(page_title="Spring Stock Pro", layout="wide")

# --- 深度美化 CSS ---
st.markdown("""
    <style>
    /* 整體背景與卡片設計 */
    .stApp { background-color: #f0f2f6; }
    div[data-testid="stMetricValue"] { color: #1e88e5; }
    .stDataFrame { background-color: white; border-radius: 10px; border: 1px solid #ddd; }
    
    /* 模仿按鈕樣式 */
    .stButton>button {
        border-radius: 20px;
        border: 1px solid #1e88e5;
        color: #1e88e5;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #1e88e5; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 股票清單
MY_TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "PLTR", "TSM", "AVGO", "SMCI", "NFLX", "META", "AMZN", "GOOGL"]

@st.cache_data(ttl=300)
def get_full_data(tickers):
    data = yf.download(tickers + ['SPY'], period='2y', progress=False)
    tz = pytz.timezone('Asia/Hong_Kong')
    update_time = datetime.now(tz).strftime("%H:%M:%S")
    return data, update_time

raw_data, sync_time = get_full_data(MY_TICKERS)

# --- 頁面標題與同步時間 ---
col_t, col_s = st.columns([3, 1])
with col_t:
    st.title("🛡️ Spring Stock Strength Pro")
with col_s:
    st.markdown(f"**SYNCED**: `{sync_time} HKT`  \n`LIVE: YAHOO API`")

# --- 模仿標籤頁切換 (Tabs) ---
tab_watchlist, tab_etf, tab_sector = st.tabs(["📋 Watchlist", "📊 ETF Basis", "🧱 Sector View"])

with tab_watchlist:
    # --- 表格邏輯 ---
    summary = []
    for t in MY_TICKERS:
        close = raw_data['Close'][t]
        spy_close = raw_data['Close']['SPY']
        rel = close / spy_close
        rs_3m = (rel.iloc[-1] / rel.iloc[-63]) - 1
        
        summary.append({
            "SYMBOL": t,
            "PRICE": close.iloc[-1],
            "RS (3M)": rs_3m,
            "RS vs SPY": (close.iloc[-1]/close.iloc[-63]) - (spy_close.iloc[-1]/spy_close.iloc[-63]),
            "VCP": "🎯 VCP" if (close.iloc[-20:].std() / close.iloc[-20:].mean() < 0.05) else "-"
        })
    
    df = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)
    st.dataframe(df.style.format({"PRICE":"${:.2f}", "RS (3M)":"{:.2%}", "RS vs SPY":"{:.2%}"}), use_container_width=True, height=500)

    st.divider()
    
    # --- 圖表與時間切換 ---
    c1, c2 = st.columns([1, 2])
    with c1:
        target = st.selectbox("Select Target", df['SYMBOL'].tolist())
    with c2:
        view_range = st.segmented_control("Range", ["3M", "6M", "1Y"], default="3M")
    
    days = {"3M": 63, "6M": 126, "1Y": 252}[view_range]
    h = raw_data.xs(target, axis=1, level=1).iloc[-days:]
    s = raw_data.xs('SPY', axis=1, level=1).iloc[-days:]
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name="K"), row=1, col=1)
    fig.add_trace(go.Scatter(x=h.index, y=h['Close']/s['Close'], name="RS Line", line=dict(color='#00FF00')), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with tab_etf:
    st.info("ETF 對比頁面開發中...")

with tab_sector:
    st.info("板塊熱力圖開發中...")