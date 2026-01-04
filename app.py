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
    .main-title { font-size: 34px; font-weight: 800; color: #0d47a1; }
    </style>
    """, unsafe_allow_html=True)

# 預設股票清單
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

# 基礎數據加載
raw_data = fetch_base_data(MY_TICKERS, SECTOR_ETFS)

# --- 2. 標題 ---
st.markdown('<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)

tab_watch, tab_etf, tab_sector = st.tabs(["📋 Watchlist", "📉 ETF Basis", "🧱 Sector View"])

# --- TAB 1: WATCHLIST ---
with tab_watch:
    # 新增：即時搜尋功能
    search_input = st.text_input("🔍 輸入代碼搜尋 (支援清單外股票, 如: MSTR, BTC-USD)", "").upper().strip()

    # 準備顯示清單
    display_tickers = MY_TICKERS.copy()
    
    # 如果搜尋了不在清單中的股票
    if search_input and search_input not in display_tickers:
        with st.spinner(f'正在從 Yahoo Finance 抓取 {search_input}...'):
            new_data = yf.download([search_input, 'SPY'], period='2y', progress=False)
            if not new_data.empty and ('Close' in new_data and search_input in new_data['Close']):
                # 將新數據合併或單獨處理
                temp_c = new_data['Close'][search_input]
                temp_s = new_data['Close']['SPY']
                rs_val = ((temp_c / temp_s).iloc[-1] / (temp_c / temp_s).iloc[-63]) - 1
                
                st.success(f"已找到 {search_input}！")
                # 建立一個單獨的小表格顯示搜尋結果
                search_res = pd.DataFrame([{
                    "Symbol": search_input, 
                    "Price": temp_c.iloc[-1], 
                    "Daily %": (temp_c.iloc[-1]/temp_c.iloc[-2])-1,
                    "RS (3M)": rs_val
                }])
                st.write("### 🔍 搜尋結果")
                st.dataframe(search_res.style.format({"Price":"${:.2f}", "Daily %":"{:+.2%}", "RS (3M)":"{:+.2%}"}))
                
                # 更新繪圖用的對象
                current_target = search_input
                plot_data = new_data
            else:
                st.error("找不到該股票，請檢查代碼是否正確。")
                current_target = MY_TICKERS[0]
                plot_data = raw_data
    else:
        current_target = search_input if search_input in MY_TICKERS else MY_TICKERS[0]
        plot_data = raw_data

    # 原有的 Watchlist 表格過濾 (僅顯示清單內)
    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close'].columns: continue
        c = raw_data['Close'][t]
        s = raw_data['Close']['SPY']
        rs_3m = ((c/s).iloc[-1] / (c/s).iloc[-63]) - 1
        summary.append({"Symbol": t, "Price": c.iloc[-1], "Daily %": (c.iloc[-1]/c.iloc[-2])-1, "RS (3M)": rs_3m})
    
    df_main = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)
    st.write("### 📋 我的監控清單")
    st.dataframe(df_main.style.format({"Price":"${:.2f}", "Daily %":"{:+.2%}", "RS (3M)":"{:+.2%}"}).background_gradient(subset=["RS (3M)"], cmap="RdYlGn"), use_container_width=True, height=300)

    st.divider()

    # --- 圖表區 (支持時間切換) ---
    st.subheader(f"📈 {current_target} 技術分析")
    c_period, c_tv = st.columns([2, 1])
    with c_period:
        p_choice = st.radio("時間範圍", ["1M", "3M", "6M", "1Y"], index=1, horizontal=True)
    with c_tv:
        st.link_button(f"🚀 TradingView: {current_target}", f"https://www.tradingview.com/chart/?symbol={current_target}", use_container_width=True)

    days = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252}[p_choice]
    
    # 取得繪圖數據
    try:
        if current_target == search_input and search_input not in MY_TICKERS:
            h = plot_data.xs(current_target, axis=1, level=1).iloc[-days:]
            spy_h = plot_data.xs('SPY', axis=1, level=1).iloc[-days:]
        else:
            h = raw_data.xs(current_target, axis=1, level=1).iloc[-days:]
            spy_h = raw_data.xs('SPY', axis=1, level=1).iloc[-days:]

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.55, 0.15, 0.3])
        fig.add_trace(go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name="K"), row=1, col=1)
        fig.add_trace(go.Bar(x=h.index, y=h['Volume'], name="Vol", marker_color='gray'), row=2, col=1)
        fig.add_trace(go.Scatter(x=h.index, y=h['Close']/spy_h['Close'], name="RS Line", line=dict(color='#00e676')), row=3, col=1)
        fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("無法載入圖表數據。")

# --- TAB 2: ETF BASIS (保持之前的功能) ---
# ... (此處保留之前的 ETF 表格與 SPY 圖表代碼) ...