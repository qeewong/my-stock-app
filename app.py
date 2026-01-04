import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 1. 頁面配置與 CSS ---
st.set_page_config(page_title="NAT LIST", layout="wide")

st.markdown("""
    <style>
    :root { --bg-clr: #f4f7f9; --txt-clr: #1e1e1e; --title-clr: #0d47a1; }
    @media (prefers-color-scheme: dark) {
        :root { --bg-clr: #0e1117; --txt-clr: #fafafa; --title-clr: #64b5f6; }
    }
    .stApp { background-color: var(--bg-clr); color: var(--txt-clr); }
    .main-title { font-size: 34px; font-weight: 800; color: var(--title-clr); margin-bottom: 10px; }
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

@st.cache_data(ttl=300)
def fetch_data(tickers, etfs):
    all_symbols = list(set(tickers + etfs + ['SPY']))
    data = yf.download(all_symbols, period='2y', progress=False)
    tz = pytz.timezone('Asia/Hong_Kong')
    st_time = datetime.now(tz).strftime("%H:%M:%S")
    return data, st_time

raw_data, sync_time = fetch_data(MY_TICKERS, SECTOR_ETFS)

# --- 2. 標題 ---
st.markdown('<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)
st.write(f"**SYNCED**: `{sync_time} HKT` | **MODE**: `iOS ADAPTIVE`")

# --- 3. 分頁 ---
tab_watch, tab_etf, tab_sector = st.tabs(["📋 Watchlist", "📉 ETF Basis", "🧱 Sector View"])

with tab_watch:
    # 搜尋框
    search_input = st.text_input("🔍 搜尋/抓取代碼 (例如: MSTR, BTC-USD)", "").upper().strip()
    
    # 計算清單數據
    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close'].columns: continue
        c_price = raw_data['Close'][t]
        s_price = raw_data['Close']['SPY']
        rs_val = ((c_price/s_price).iloc[-1] / (c_price/s_price).iloc[-63]) - 1
        summary.append({
            "Symbol": t, "Price": c_price.iloc[-1], 
            "Daily %": (c_price.iloc[-1]/c_price.iloc[-2])-1, 
            "RS (3M)": rs_val
        })
    df_main = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)

    # 顯示表格
    st.dataframe(df_main.style.format({"Price":"${:.2f}","Daily %":"{:+.2%}","RS (3M)":"{:+.2%}"})
                 .background_gradient(subset=["RS (3M)"], cmap="RdYlGn"), use_container_width=True, height=350)

    st.divider()

    # 圖表對象決定
    if search_input and search_input not in MY_TICKERS:
        plot_target = search_input
        # 即時抓取清單外數據
        with st.spinner(f"Fetching {search_input}..."):
            plot_h = yf.download([plot_target, 'SPY'], period='2y', progress=False)
    else:
        plot_target = search_input if search_input in MY_TICKERS else df_main['Symbol'].iloc[0]
        plot_h = raw_data

    # 控制器
    c1, c2, c3 = st.columns([1, 1, 1.2])
    with c1: target = st.selectbox("分析對象", [plot_target] + df_main['Symbol'].tolist())
    with c2: period = st.radio("範圍", ["3M", "6M", "1Y"], horizontal=True)
    with c3: st.link_button(f"🚀 TRADINGVIEW: {target}", f"https://www.tradingview.com/chart/?symbol={target}", use_container_width=True)

    # 繪製 K線 + RS Line
    days = {"3M": 63, "6M": 126, "1Y": 252}[period]
    try:
        # 處理多層或單層 Index
        if isinstance(plot_h.columns, pd.MultiIndex):
            h = plot_h.xs(target, axis=1, level=1).iloc[-days:]
            spy_h = raw_data.xs('SPY', axis=1, level=1).iloc[-days:]
        else:
            h = plot_h.iloc[-days:] # 針對單一搜尋結果
            spy_h = yf.download('SPY', period='2y', progress=False).iloc[-days:]

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.3])
        # 1. K線
        fig.add_trace(go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name="Price"), row=1, col=1)
        # 2. 成交量 (紅綠)
        v_cols = ['#ef5350' if h['Open'].iloc[i] > h['Close'].iloc[i] else '#26a69a' for i in range(len(h))]
        fig.add_trace(go.Bar(x=h.index, y=h['Volume'], name="Vol", marker_color=v_cols), row=2, col=1)
        # 3. RS Line
        rs_line = h['Close'] / spy_h['Close']
        fig.add_trace(go.Scatter(x=h.index, y=rs_line, name="RS Line", line=dict(color='#00e676', width=2)), row=3, col=1)

        fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"請輸入正確代碼以顯示圖表 ({e})")

with tab_etf:
    st.subheader("🇺🇸 S&P 500 Index (SPY) Chart")
    spy_p = raw_data.xs('SPY', axis=1, level=1).iloc[-126:]
    fig