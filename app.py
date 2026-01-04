import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 1. 頁面配置 ---
st.set_page_config(page_title="NAT LIST", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .main-title { font-size: 36px; font-weight: 900; color: #0d47a1; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

# 股票清單與 11 隻板塊 ETF
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
def fetch_all_market_data(tickers, etfs):
    indices = ['SPY', 'QQQ', 'IWM']
    all_symbols = list(set(tickers + etfs + indices))
    data = yf.download(all_symbols, period='2y', progress=False)
    tz = pytz.timezone('Asia/Hong_Kong')
    sync_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    return data, sync_time

raw_data, sync_time = fetch_all_market_data(MY_TICKERS, SECTOR_ETFS)

# --- 2. 頁面頭部 ---
st.markdown('<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)
st.markdown(f"**SYNCED**: `{sync_time} HKT` | **LIVE DATA**")

tab_watch, tab_etf, tab_sector = st.tabs(["📊 Watchlist", "📉 ETF Basis", "🧱 Sector View"])

# --- TAB 1: WATCHLIST (保持之前修復好的狀態) ---
with tab_watch:
    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close'].columns: continue
        c = raw_data['Close'][t]
        s = raw_data['Close']['SPY']
        rs_3m = ( (c/s).iloc[-1] / (c/s).iloc