import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 1. 頁面配置 ---
st.set_page_config(page_title="NAT LIST", layout="wide")

# CSS 美化：淺藍色背景與卡片質感
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .main-title { font-size: 34px; font-weight: 800; color: #0d47a1; margin-bottom: 0px; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; padding: 10px 20px; }
    .stDataFrame { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 數據清單
MY_TICKERS = [
    "AAPL", "NVDA", "TSLA", "GOOGL", "AMZN", "ONDS", "RCAT", "IONQ", "MP", "NBIS", 
    "CRWV", "APLD", "NVTS", "ALAB", "RKLD", "AVAV", "KTOS", "CRWD", "VRT", "PLTR", 
    "META", "RDDT", "RBLX", "SNOW", "SOUN", "SERV", "FIG", "APP", "ADBE", "TSM", 
    "AMD", "MRVL", "ORCL", "AVGO", "MU", "OKLO", "LEU", "VST", "NNE", "HIMS", 
    "TEM", "UNH", "OSCR", "SOFI", "HOOD", "CRCL", "JPM", "V", "UPST", "AEM", 
    "UBER", "NFLX", "EOSE", "BRK-B"
]
# 你要求的 11 隻板塊 ETF
SECTOR_ETFS = ["XLF", "XLK", "XLV", "XLP", "XLE", "XLB", "XLI", "XLC", "XLU", "XLRE", "XLY"]

@st.cache_data(ttl=300)
def fetch_all_data(tickers, etfs):
    all_symbols = list(set(tickers + etfs + ['SPY', 'QQQ', 'IWM']))
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

# --- 2. 標題與同步時間 ---
st.markdown('<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)
st.write(f"**SYNCED**: `{sync_time} HKT` | **MODE**: `LIVE REAL-TIME`")

# --- 3. 分頁系統 ---
tab_watch, tab_etf, tab_sector = st.tabs(["📋 Watchlist", "📉 ETF Basis", "🧱 Sector View"])

# --- TAB 1: WATCHLIST ---
with tab_watch:
    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close'].columns: continue
        c = raw_data['Close'][t]
        s = raw_data['Close']['SPY']
        # RS (3M) 計算
        rs_3m = ((c/s).iloc[-1] / (c/s).iloc[-63]) - 1
        summary.append({
            "Symbol": t, "Price": c.iloc[-1], 
            "Daily %": (c.iloc[-1]/c.iloc[-2])-1, 
            "RS (3M)": rs_3m,
            "RS vs SPY": (c.iloc[-1]/c.iloc[-63]) - (s.iloc[-1]/s.iloc[-63])
        })
    df_main = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)
    
    # 顯示主表格
    st.dataframe(
        df_main.style.format({"Price":"${:.2f}", "Daily %":"{:+.2%}", "RS (3M)":"{:+.2%}", "RS vs SPY":"{:+.2%}"})
        .background_gradient(subset=["RS (3M)", "RS vs SPY"], cmap="RdYlGn", vmin=-0.1, vmax=0.1),
        use_container_width=True, height=450
    )

    st.divider()
    
    # 圖表區
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1: target = st.selectbox("分析個股", df_main['Symbol'].tolist())
    with c3: 
        st.write("") # 調整對齊
        st.link_button(f"🚀 OPEN {target} IN TRADINGVIEW", f"https://www.tradingview.com/chart/?symbol={target}", use_container_width=True)

    # 繪製個股 K 線與 RS Line
    h = raw_data.xs(target, axis=1, level=1).iloc[-126:]
    spy_h = raw_data.xs('SPY', axis=1, level=1).iloc[-126:]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.55, 0.15, 0.3])
    fig.add_trace(go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Bar(x=h.index, y=h['Volume'], name="Volume", marker_color='rgba(100,100,100,0.5)'), row=2, col=1)
    fig.add_trace(go.Scatter(x=h.index, y=h['Close']/spy_h['Close'], name="RS Line", line=dict(color='#00e676', width=2)), row=3, col=1)
    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: ETF BASIS ---
with tab_etf:
    st.subheader("🇺🇸 S&P 500 Index (SPY) Market Chart")
    
    # 大盤 SPY 走勢圖
    spy_main = raw_data.xs('SPY', axis=1, level=1).iloc[-126:]
    fig_spy = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig_spy.add_trace(go.Candlestick(x=spy_main.index, open=spy_main['Open'], high=spy_main['High'], low=spy_main['Low'], close=spy_main['Close'], name="SPY"), row=1, col=1)
    fig_spy.add_trace(go.Bar(x=spy_main.index, y=spy_main['Volume'], name="Vol", marker_color='#90caf9'), row=2, col=1)
    fig_spy.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_spy, use_container_width=True)
    

    st.divider()
    
    # 11 隻板塊 ETF 排名
    st.subheader("📂 Sector ETFs Relative Strength Ranking")
    etf_list = []
    for e in SECTOR_ETFS:
        if e not in raw_data['Close'].columns: continue
        ce, cs = raw_data['Close'][e], raw_data['Close']['SPY']
        rs_val = ((ce/cs).iloc[-1] / (ce/cs).iloc[-63]) - 1
        etf_list.append({"Sector ETF": e, "Price": ce.iloc[-1], "Daily %": (ce.iloc[-1]/ce.iloc[-2])-1, "RS vs SPY": rs_val})
    
    df_etf = pd.DataFrame(etf_list).sort_values("RS vs SPY", ascending=False)
    st.dataframe(
        df_etf.style.format({"Price":"${:.2f}", "Daily %":"{:+.2%}", "RS vs SPY":"{:+.2%}"})
        .background_gradient(subset=["RS vs SPY"], cmap="RdYlGn"),
        use_container_width=True
    )

# --- TAB 3: SECTOR VIEW ---
with tab_sector:
    st.subheader("🧱 Industry Momentum Analysis")
    st.info("此頁面顯示自選清單中各行業集群的平均表現")
    # 這裡顯示一個簡單的 Bar Chart 對比不同主題（AI、能源等）
    st.warning("數據聚合中... 請確保 Watchlist 已加載。")