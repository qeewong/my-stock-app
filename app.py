import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 1. 頁面配置 ---
st.set_page_config(page_title="NAT LIST", layout="wide")

# 自定義 CSS 美化
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .main-title { font-size: 32px; font-weight: 800; color: #1e1e1e; margin-bottom: 20px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; white-space: pre-wrap; background-color: #f0f2f6; 
        border-radius: 10px 10px 0px 0px; gap: 1px; padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #1e88e5; }
    /* 讓按鈕更顯眼 */
    .stLinkButton > a {
        background-color: #1e88e5 !important;
        color: white !important;
        font-weight: bold;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# 股票清單
MY_TICKERS = [
    "AAPL", "NVDA", "TSLA", "GOOGL", "AMZN", "ONDS", "RCAT", "IONQ", "MP", "NBIS", 
    "CRWV", "APLD", "NVTS", "ALAB", "RKLD", "AVAV", "KTOS", "CRWD", "VRT", "PLTR", 
    "META", "RDDT", "RBLX", "SNOW", "SOUN", "SERV", "FIG", "APP", "ADBE", "TSM", 
    "AMD", "MRVL", "ORCL", "AVGO", "MU", "OKLO", "LEU", "VST", "NNE", "HIMS", 
    "TEM", "UNH", "OSCR", "SOFI", "HOOD", "CRCL", "JPM", "V", "UPST", "AEM", 
    "UBER", "NFLX", "EOSE", "BRK-B"
]

@st.cache_data(ttl=300)
def fetch_all_data(tickers):
    indices = ['SPY', 'QQQ', 'IWM']
    all_to_fetch = list(set(tickers + indices))
    data = yf.download(all_to_fetch, period='2y', progress=False)
    
    # 建立板塊字典 (簡化版：將代號歸類以便 Sector View 顯示)
    # 實際上可以透過 yf.Ticker 抓取，但為了速度我們先自定義大類
    sector_map = {
        "AI/Tech": ["NVDA", "TSM", "AMD", "AVGO", "MSFT", "PLTR", "SOUN", "SERV", "ALAB"],
        "SaaS/Software": ["ADBE", "CRM", "SNOW", "ORCL", "APP", "CRWD"],
        "Consumer/Social": ["AAPL", "TSLA", "META", "AMZN", "GOOGL", "RDDT", "NFLX"],
        "Defense/Energy": ["AVAV", "KTOS", "OKLO", "LEU", "VST", "NNE", "RCAT"],
        "Finance/Health": ["JPM", "V", "SOFI", "HOOD", "UNH", "HIMS", "OSCR"]
    }
    
    tz = pytz.timezone('Asia/Hong_Kong')
    sync_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    return data, sync_time, sector_map

raw_data, sync_time, sector_groups = fetch_all_data(MY_TICKERS)

# --- 標題區域 ---
st.markdown(f'<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)
st.markdown(f"**SYNCED**: `{sync_time} HKT` | **SOURCE**: `YAHOO FINANCE`")

# --- 分頁系統 ---
tab_watch, tab_etf, tab_sector = st.tabs(["📋 Watchlist", "📉 ETF Basis", "🧱 Sectors"])

with tab_watch:
    # 1. 數據表格
    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close']: continue
        price = raw_data['Close'][t].iloc[-1]
        change = (price / raw_data['Close'][t].iloc[-2]) - 1
        rel = raw_data['Close'][t] / raw_data['Close']['SPY']
        rs_3m = (rel.iloc[-1] / rel.iloc[-63]) - 1
        rs_vs_spy = (price/raw_data['Close'][t].iloc[-63]) - (raw_data['Close']['SPY'].iloc[-1]/raw_data['Close']['SPY'].iloc[-63])
        
        summary.append({
            "Symbol": t, "Price": price, "Daily %": change,
            "RS (3M)": rs_3m, "RS vs SPY": rs_vs_spy,
            "VCP Status": "🎯 VCP" if (raw_data['Close'][t].iloc[-20:].std()/price < 0.03) else "-"
        })
    
    df_main = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)
    st.dataframe(
        df_main.style.format({
            "Price": "${:.2f}", "Daily %": "{:+.2%}", 
            "RS (3M)": "{:+.2%}", "RS vs SPY": "{:+.2%}"
        }).background_gradient(subset=["RS (3M)", "RS vs SPY"], cmap="RdYlGn", vmin=-0.2, vmax=0.2),
        use_container_width=True, height=500
    )

    st.divider()
    
    # 2. 圖表與 One-Click TradingView
    c1, c2, c3 = st.columns([1.5, 2, 1.5])
    with c1:
        target = st.selectbox("分析對象", df_main['Symbol'].tolist())
    with c2:
        trange = st.radio("Range", ["3M", "6M", "1Y"], horizontal=True)
    with c3:
        # --- 恢復 One Click 跳轉按鈕 ---
        st.write("") # 調整對齊
        tv_url = f"https://www.tradingview.com/chart/?symbol={target}"
        st.link_button(f"🚀 OPEN IN TRADINGVIEW", tv_url, use_container_width=True)
    
    # 繪圖邏輯
    days = {"3M": 63, "6M": 126, "1Y": 252}[trange]