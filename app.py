import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 1. 頁面配置 ---
st.set_page_config(page_title="NAT LIST", layout="wide")

# 動態 CSS：適配系統 Dark/Light Mode
st.markdown("""
    <style>
    /* 預設 Light Mode 樣式 */
    :root {
        --bg-color: #f4f7f9;
        --text-color: #1e1e1e;
        --card-bg: #ffffff;
        --title-color: #0d47a1;
    }

    /* 當系統開啟 Dark Mode 時自動切換變量 */
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-color: #0e1117;
            --text-color: #fafafa;
            --card-bg: #1e2128;
            --title-color: #64b5f6;
        }
    }

    .stApp { background-color: var(--bg-color); color: var(--text-color); }
    .main-title { font-size: 34px; font-weight: 800; color: var(--title-color); }
    
    /* 確保表格與卡片在 Dark Mode 下清晰 */
    .stDataFrame, .stTable { 
        background-color: var(--card-bg) !important; 
        border-radius: 10px; 
    }
    
    /* 修改 Input 框文字顏色以防在暗黑模式下看不見 */
    input { color: var(--text-color) !important; }
    </style>
    """, unsafe_allow_html=True)

# 預設清單
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
def fetch_base_data(tickers, etfs):
    all_symbols = list(set(tickers + etfs + ['SPY']))
    data = yf.download(all_symbols, period='2y', progress=False)
    return data

raw_data = fetch_base_data(MY_TICKERS, SECTOR_ETFS)

# --- 2. 標題 ---
st.markdown('<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)

# --- 3. 分頁與內容 ---
tab_watch, tab_etf, tab_sector = st.tabs(["📋 Watchlist", "📉 ETF Basis", "🧱 Sector View"])

with tab_watch:
    search_input = st.text_input("🔍 搜尋代碼 (如: MSTR, BTC-USD)", "").upper().strip()
    
    # ... (此處保留之前的搜尋與數據處理邏輯) ...
    # 建立數據摘要
    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close'].columns: continue
        c = raw_data['Close'][t]
        s = raw_data['Close']['SPY']
        rs_3m = ((c/s).iloc[-1] / (c/s).iloc[-63]) - 1
        summary.append({"Symbol": t, "Price": c.iloc[-1], "Daily %": (c.iloc[-1]/c.iloc[-2])-1, "RS (3M)": rs_3m})
    
    df_main = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)
    
    # 這裡使用透明背景的 Table 樣式，確保在 Dark Mode 下不會有白色方塊
    st.dataframe(
        df_main.style.format({"Price":"${:.2f}", "Daily %":"{:+.2%}", "RS (3M)":"{:+.2%}"})
        .background_gradient(subset=["RS (3M)"], cmap="RdYlGn"), 
        use_container_width=True, height=400
    )

    # 圖表控制項
    st.divider()
    target = st.selectbox("分析對象", [search_input] + df_main['Symbol'].tolist() if search_input else df_main['Symbol'].tolist())
    p_choice = st.radio("範圍", ["1M", "3M", "6M", "1Y"], index=1, horizontal=True)

    # 圖表繪製：Plotly 自動適配背景
    # 我們設定 template 為 None，讓它自動跟隨 Streamlit 的主題
    h = yf.download(target, period='2y', progress=False) if target not in MY_TICKERS else raw_data.xs(target, axis=1, level=1)
    spy_h = raw_data.xs('SPY', axis=1, level=1)
    
    days = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252}[p_choice]
    h = h.iloc[-days:]
    spy_slice = spy_h.iloc[-days:]

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.55, 0.15, 0.3])
    fig.add_trace(go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name="K"), row=1, col=1)
    fig.add_trace(go.Bar(x=h.index, y=h['Volume'], name="Vol", marker_color='gray'), row=2, col=1)
    fig.add_trace(go.Scatter(x=h.index, y=h['Close']/spy_slice['Close'], name="RS", line=dict(color='#00e676')), row=3, col=1)
    
    # 重要：不要強制 template="plotly_dark"，改用自動主題
    fig.update_layout(height=700, xaxis_rangeslider_visible=False, margin=dict(t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)