import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 網頁配置 ---
st.set_page_config(page_title="RS & VCP 專業監控", layout="wide")

# --- 1. 你的自選股票清單 (已更新) ---
MY_TICKERS = [
    "AAPL", "NVDA", "TSLA", "GOOGL", "AMZN", "ONDS", "RCAT", "IONQ", "MP", "NBIS", 
    "CRWV", "APLD", "NVTS", "ALAB", "RKLD", "AVAV", "KTOS", "CRWD", "VRT", "PLTR", 
    "META", "RDDT", "RBLX", "SNOW", "SOUN", "SERV", "FIG", "APP", "ADBE", "TSM", 
    "AMD", "MRVL", "ORCL", "AVGO", "MU", "OKLO", "LEU", "VST", "NNE", "HIMS", 
    "TEM", "UNH", "OSCR", "SOFI", "HOOD", "CRCL", "JPM", "V", "UPST", "AEM", 
    "UBER", "NFLX", "EOSE", "BRK-B" # yfinance 中 BRK.B 需寫成 BRK-B
]

# 板塊翻譯字典
SECTOR_MAP = {
    "Technology": "電子科技", "Communication Services": "通訊服務",
    "Consumer Cyclical": "週期性消費", "Financial Services": "金融服務",
    "Healthcare": "醫療保健", "Energy": "能源", "Industrials": "工業",
    "Basic Materials": "基礎材料", "Utilities": "公共事業", "Real Estate": "房地產"
}

# --- 2. 核心功能函數 ---
@st.cache_data(ttl=3600)
def fetch_everything(tickers):
    all_symbols = tickers + ['SPY']
    # 抓取 1 年數據以計算 50MA 和 RS
    data = yf.download(all_symbols, period='1y', progress=False)
    close_df = data['Close']
    
    # 抓取個股資訊 (板塊)
    summary_list = []
    for t in tickers:
        if t not in close_df.columns: continue
        
        # 計算指標
        ma10 = close_df[t].rolling(10).mean().iloc[-1]
        ma20 = close_df[t].rolling(20).mean().iloc[-1]
        ma50 = close_df[t].rolling(50).mean().iloc[-1]
        
        rel_perf = (close_df[t] / close