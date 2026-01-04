import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pytz

# --- 1. 頁面配置 ---
st.set_page_config(page_title="NAT LIST", layout="wide")

# CSS 美化
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .main-title { font-size: 34px; font-weight: 800; color: #0d47a1; margin-bottom: 0px; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; padding: 10px 20px; }
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
def fetch_all_data(tickers, etfs):
    all_symbols = list(set(tickers + etfs + ['SPY']))
    data = yf.download(all_symbols, period='2y', progress=False)
    tz = pytz.timezone('Asia/Hong_Kong')
    sync_time = datetime.now(tz).strftime("%H:%M:%S")
    return data, sync_time

# 抓取數據
try:
    raw_data, sync_time = fetch_all_data(MY_TICKERS, SECTOR_ETFS)
except Exception as e:
    st.error(f"數據加載失敗: {e}")
    st.stop()

# --- 2. 標題 ---
st.markdown('<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)
st.write(f"**SYNCED**: `{sync_time} HKT` | **MODE**: `LIVE REAL-TIME`")

# --- 3. 分頁系統 ---
tab_watch, tab_etf, tab_sector = st.tabs(["📋 Watchlist", "📉 ETF Basis", "🧱 Sector View"])

# --- TAB 1: WATCHLIST ---
with tab_watch:
    # --- 搜尋與過濾功能 ---
    search_query = st.text_input("🔍 搜尋股票代碼 (例如: NVDA)", "").upper()

    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close'].columns: continue
        c = raw_data['Close'][t]
        s = raw_data['Close']['SPY']
        rs_3m = ((c/s).iloc[-1] / (c/s).iloc[-63]) - 1
        summary.append({
            "Symbol": t, "Price": c.iloc[-1], 
            "Daily %": (c.iloc[-1]/c.iloc[-2])-1, 
            "RS (3M)": rs_3m
        })
    
    df_main = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)

    # 執行搜尋過濾
    if search_query:
        df_display = df_main[df_main['Symbol'].str.contains(search_query)]
    else:
        df_display = df_main

    st.dataframe(
        df_display.style.format({"Price":"${:.2f}", "Daily %":"{:+.2%}", "RS (3M)":"{:+.2%}"})
        .background_gradient(subset=["RS (3M)"], cmap="RdYlGn"),
        use_container_width=True, height=350
    )

    st.divider()
    
    # --- 圖表區控制 ---
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        target = st.selectbox("分析個股", df_main['Symbol'].tolist())
    with c2:
        period_choice = st.radio("時間區間", ["1M", "3M", "6M", "1Y"], index=1, horizontal=True)
    with c3:
        st.link_button(f"🚀 OPEN {target} IN TRADINGVIEW", f"https://www.tradingview.com/chart/?symbol={target}", use_container_width=True)

    # 根據選擇計算顯示天數
    days_map = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252}
    display_days = days_map[period_choice]

    h = raw_data.xs(target, axis=1, level=1).iloc[-display_days:]
    spy_h = raw_data.xs('SPY', axis=1, level=1).iloc[-display_days:]
    
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.55, 0.15, 0.3])
    
    # K線圖
    fig.add_trace(go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name=f"{target} Price"), row=1, col=1)
    # 成交量
    fig.add_trace(go.Bar(x=h.index, y=h['Volume'], name="Volume", marker_color='gray', opacity=0.5), row=2, col=1)
    # RS 線 (Relative Strength Line)
    fig.add_trace(go.Scatter(x=h.index, y=h['Close']/spy_h['Close'], name="RS Line", line=dict(color='#00e676', width=2)), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, margin=dict(t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: ETF BASIS ---
with tab_etf:
    st.subheader("🇺🇸 S&P 500 Index (SPY) Market Status")
    spy_main = raw_data.xs('SPY', axis=1, level=1).iloc[-126:]
    fig_spy = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig_spy.add_trace(go.Candlestick(x=spy_main.index, open=spy_main['Open'], high=spy_main['High'], low=spy_main['Low'], close=spy_main['Close'], name="SPY"), row=1, col=1)
    fig_spy.add_trace(go.Bar(x=spy_main.index, y=spy_main['Volume'], name="Vol", marker_color='#90caf9'), row=2, col=1)
    fig_spy.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_spy, use_container_width=True)

    st.subheader("📂 Sector ETF Ranking (Relative to SPY)")
    etf_list = []
    for e in SECTOR_ETFS:
        if e not in raw_data['Close'].columns: continue
        ce, cs = raw_data['Close'][e], raw_data['Close']['SPY']
        rs_val = ((ce/cs).iloc[-1] / (ce/cs).iloc[-63]) - 1
        etf_list.append({"Sector ETF": e, "Price": ce.iloc[-1], "RS vs SPY": rs_val})
    
    df_etf = pd.DataFrame(etf_list).sort_values("RS vs SPY", ascending=False)
    st.dataframe(df_etf.style.format({"Price":"${:.2f}", "RS vs SPY":"{:+.2%}"}).background_gradient(subset=["RS vs SPY"], cmap="RdYlGn"), use_container_width=True)

# --- TAB 3: SECTOR VIEW ---
with tab_sector:
    st.info("此頁面正根據 Watchlist 數據進行板塊熱力圖聚合分析。")
    st.write("目前顯示：11 隻板塊 ETF 平均強度。")