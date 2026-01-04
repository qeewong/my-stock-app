import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 1. 頁面配置 ---
st.set_page_config(page_title="NAT LIST", layout="wide")

# 動態 CSS 適配 (支持 iOS Dark Mode)
st.markdown("""
    <style>
    :root { --bg-clr: #f4f7f9; --txt-clr: #1e1e1e; --title-clr: #0d47a1; --card-bg: #ffffff; }
    @media (prefers-color-scheme: dark) {
        :root { --bg-clr: #0e1117; --txt-clr: #fafafa; --title-clr: #64b5f6; --card-bg: #1e2128; }
    }
    .stApp { background-color: var(--bg-clr); color: var(--txt-clr); }
    .main-title { font-size: 34px; font-weight: 800; color: var(--title-clr); margin-bottom: 0px; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; padding: 10px 20px; }
    /* 強制修改表格文字顏色適配暗黑模式 */
    .stDataFrame { background-color: var(--card-bg); border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 股票與 ETF 清單
MY_TICKERS = [
    "AAPL", "NVDA", "TSLA", "GOOGL", "AMZN", "ONDS", "RCAT", "IONQ", "MP", "NBIS", 
    "CRWV", "APLD", "NVTS", "ALAB", "RKLD", "AVAV", "KTOS", "CRWD", "VRT", "PLTR", 
    "META", "RDDT", "RBLX", "SNOW", "SOUN", "SERV", "FIG", "APP", "ADBE", "TSM", 
    "AMD", "MRVL", "ORCL", "AVGO", "MU", "OKLO", "LEU", "VST", "NNE", "HIMS", 
    "TEM", "UNH", "OSCR", "SOFI", "HOOD", "CRCL", "JPM", "V", "UPST", "AEM", 
    "UBER", "NFLX", "EOSE", "BRK-B"
]
SECTOR_ETFS = ["XLF", "XLK", "XLV", "XLP", "XLE", "XLB", "XLI", "XLC", "XLU", "XLRE", "XLY"]

@st.cache_data(ttl=300)
def fetch_full_data(tickers, etfs):
    all_syms = list(set(tickers + etfs + ['SPY']))
    data = yf.download(all_syms, period='2y', progress=False)
    tz = pytz.timezone('Asia/Hong_Kong')
    sync_t = datetime.now(tz).strftime("%H:%M:%S")
    return data, sync_t

raw_data, sync_time = fetch_full_data(MY_TICKERS, SECTOR_ETFS)

# --- 2. 標題 ---
st.markdown('<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)
st.write(f"**SYNCED**: `{sync_time} HKT` | **MODE**: `LIVE REAL-TIME`")

# --- 3. 分頁系統 ---
tab_watch, tab_etf, tab_sector = st.tabs(["📋 Watchlist", "📉 ETF Basis", "🧱 Sector View"])

# --- TAB 1: WATCHLIST ---
with tab_watch:
    search_q = st.text_input("🔍 搜尋/抓取代碼 (例如: MSTR, BTC-USD)", "").upper().strip()
    
    # 核心數據處理
    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close'].columns: continue
        c = raw_data['Close'][t]
        s = raw_data['Close']['SPY']
        rs_3m = ((c/s).iloc[-1] / (c/s).iloc[-63]) - 1
        summary.append({"Symbol": t, "Price": c.iloc[-1], "Daily %": (c.iloc[-1]/c.iloc[-2])-1, "RS (3M)": rs_3m})
    
    df_main = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)
    
    # 如果有搜尋清單外的股票
    current_target = MY_TICKERS[0]
    if search_q:
        if search_q in MY_TICKERS:
            current_target = search_q
        else:
            try:
                s_data = yf.download([search_q, 'SPY'], period='1y', progress=False)
                sc, ss = s_data['Close'][search_q], s_data['Close']['SPY']
                s_rs = ((sc/ss).iloc[-1] / (sc/ss).iloc[-63]) - 1
                search_row = pd.DataFrame([{"Symbol": search_q, "Price": sc.iloc[-1], "Daily %": (sc.iloc[-1]/sc.iloc[-2])-1, "RS (3M)": s_rs}])
                st.write("### 🔍 Search Result")
                st.dataframe(search_row.style.format({"Price":"${:.2f}", "Daily %":"{:+.2%}", "RS (3M)":"{:+.2%}"}))
                current_target = search_q
            except: st.error("Invalid Ticker")

    st.write("### 📋 Watchlist Table")
    st.dataframe(df_main.style.format({"Price":"${:.2f}","Daily %":"{:+.2%}","RS (3M)":"{:+.2%}"}).background_gradient(subset=["RS (3M)"], cmap="RdYlGn"), use_container_width=True, height=350)

    st.divider()