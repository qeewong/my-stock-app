import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz
import numpy as np

# --- 1. 頁面配置 ---
st.set_page_config(page_title="NAT LIST", layout="wide")

# CSS 適配 iOS Dark Mode (保持不變)
st.markdown("""
    <style>
    :root { --bg-clr: #f4f7f9; --txt-clr: #1e1e1e; --title-clr: #0d47a1; }
    @media (prefers-color-scheme: dark) {
        :root { --bg-clr: #0e1117; --txt-clr: #fafafa; --title-clr: #64b5f6; }
    }
    .stApp { background-color: var(--bg-clr); color: var(--txt-clr); }
    .main-title { font-size: 34px; font-weight: 800; color: var(--title-clr); margin-bottom: 5px; }
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
SECTOR_ETFS = ["XLF", "XLK", "XLV", "XLP", "XLE", "XLB", "XLI", "XLC", "XLU", "XLRE", "XLY"]

# VCP 判定邏輯函數
def check_vcp(prices, volumes):
    """
    簡單 VCP 判定：
    1. 近 20 天波動率低於近 60 天波動率 (收窄)
    2. 價格高於 50日及 200日均線 (趨勢向上)
    3. 成交量在盤整期萎縮
    """
    if len(prices) < 200: return "-"
    
    recent_volatility = prices.iloc[-20:].std() / prices.iloc[-20:].mean()
    base_volatility = prices.iloc[-60:].std() / prices.iloc[-60:].mean()
    
    sma50 = prices.rolling(50).mean().iloc[-1]
    sma200 = prices.rolling(200).mean().iloc[-1]
    
    # 判定條件：波動收窄 + 價格處於上升趨勢
    if recent_volatility < base_volatility * 0.7 and prices.iloc[-1] > sma50 > sma200:
        return "🎯 VCP"
    return "-"

@st.cache_data(ttl=300)
def fetch_all_data(tickers, etfs):
    all_syms = list(set(tickers + etfs + ['SPY']))
    data = yf.download(all_syms, period='2y', progress=False)
    tz = pytz.timezone('Asia/Hong_Kong')
    st_time = datetime.now(tz).strftime("%H:%M:%S")
    return data, st_time

raw_data, sync_time = fetch_all_data(MY_TICKERS, SECTOR_ETFS)

# --- 2. 標題 ---
st.markdown('<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)
st.write(f"**SYNCED**: `{sync_time} HKT` | **MODE**: `STABLE`")

# --- 3. 分頁 ---
tab_watch, tab_etf, tab_sector = st.tabs(["📋 Watchlist", "📉 ETF Basis", "🧱 Sector View"])

# --- TAB 1: WATCHLIST ---
with tab_watch:
    search_q = st.text_input("🔍 搜尋/抓取代碼", "", key="main_search").upper().strip()
    
    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close'].columns: continue
        c = raw_data['Close'][t]
        v = raw_data['Volume'][t]
        s = raw_data['Close']['SPY']
        
        rs_3m = ((c/s).iloc[-1] / (c/s).iloc[-63]) - 1
        
        # 呼叫 VCP 判定
        vcp_status = check_vcp(c, v)
        
        summary.append({
            "Symbol": t, 
            "Price": c.iloc[-1], 
            "Daily %": (c.iloc[-1]/c.iloc[-2])-1, 
            "RS (3M)": rs_3m,
            "Pattern": vcp_status  # 新增一列提示
        })
    
    df_main = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)
    # 顯示表格 (格式不變，僅多出一列 Pattern)
    st.dataframe(df_main.style.format({"Price":"${:.2f}","Daily %":"{:+.2%}","RS (3M)":"{:+.2%}"})
                 .background_gradient(subset=["RS (3M)"], cmap="RdYlGn"), use_container_width=True, height=300)

    st.divider()

    # 圖表邏輯 (保持原有邏輯)
    target = search_q if search_q else df_main['Symbol'].iloc[0]
    
    col_a, col_b, col_c = st.columns([1, 1, 1.2])
    with col_a: 
        final_target = st.selectbox("分析對象", [target] + df_main['Symbol'].tolist(), key="select_target")
    with col_b: 
        p_choice = st.radio("範圍", ["3M", "6M", "1Y"], horizontal=True, key="range_choice")
    with col_c: 
        st.link_button(f"🚀 TRADINGVIEW: {final_target}", f"https://www.tradingview.com/chart/?symbol={final_target}", use_container_width=True)

    try:
        # 使用現有繪圖邏輯
        h_all = yf.download([final_target, 'SPY'], period='2y', progress=False)
        days = {"3M": 63, "6M": 126, "1Y": 252}[p_choice]
        h = h_all['Close'][final_target].iloc[-days:]
        h_open = h_all['Open'][final_target].iloc[-days:]
        h_high = h_all['High'][final_target].iloc[-days:]
        h_low = h_all['Low'][final_target].iloc[-days:]
        h_vol = h_all['Volume'][final_target].iloc[-days:]
        spy_c = h_all['Close']['SPY'].iloc[-days:]

        fig_main = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.3])
        fig_main.add_trace(go.Candlestick(x=h.index, open=h_open, high=h_high, low=h_low, close=h, name="Price"), row=1, col=1)
        v_colors = ['#ef5350' if h_open.iloc[i] > h.iloc[i] else '#26a69a' for i in range(len(h))]
        fig_main.add_trace(go.Bar(x=h.index, y=h_vol, name="Vol", marker_color=v_colors), row=2, col=1)
        fig_main.add_trace(go.Scatter(x=h.index, y=h/spy_c, name="RS Line", line=dict(color='#00e676', width=2)), row=3, col=1)

        fig_main.update_layout(height=750, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(t=10,b=10))
        st.plotly_chart(fig_main, use_container_width=True, key="main_chart_display")
    except:
        st.error("無法載入該代碼數據")

# --- TAB 2 & 3 (保持完全不變) ---
with tab_etf:
    st.subheader("🇺🇸 S&P 500 (SPY)")
    spy_data = raw_data.xs('SPY', axis=1, level=1).iloc[-126:]
    fig_spy = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig_spy.add_trace(go.Candlestick(x=spy_data.index, open=spy_data['Open'], high=spy_data['High'], low=spy_data['Low'], close=spy_data['Close'], name="SPY"), row=1, col=1)
    s_v_cols = ['#ef5350' if spy_data['Open'].iloc[i] > spy_data['Close'].iloc[i] else '#26a69a' for i in range(len(spy_data))]
    fig_spy.add_trace(go.Bar(x=spy_data.index, y=spy_data['Volume'], name="Vol", marker_color=s_v_cols), row=2, col=1)
    fig_spy.update_layout(height=450, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig_spy, use_container_width=True, key="spy_etf_chart")

    st.subheader("📂 Sector Ranking")
    etf_summary = []
    for e in SECTOR_ETFS:
        if e not in raw_data['Close'].columns: continue
        ce, cs = raw_data['Close'][e], raw_data['Close']['SPY']
        rs_v = ((ce/cs).iloc[-1] / (ce/cs).iloc[-63]) - 1
        etf_summary.append({"ETF": e, "Price": ce.iloc[-1], "RS vs SPY": rs_v})
    df_etf = pd.DataFrame(etf_summary).sort_values("RS vs SPY", ascending=False)
    st.dataframe(df_etf.style.format({"Price":"${:.2f}","RS vs SPY":"{:+.2%}"}).background_gradient(subset=["RS vs SPY"], cmap="RdYlGn"), use_container_width=True)