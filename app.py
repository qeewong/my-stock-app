import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 1. 頁面基礎配置 ---
st.set_page_config(page_title="NAT LIST", layout="wide")

# 深度美化 CSS：恢復淺藍色背景與卡片風格
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; color: #1e1e1e; }
    .main-title { font-size: 36px; font-weight: 900; color: #0d47a1; margin-bottom: 5px; }
    .sync-info { color: #546e7a; font-size: 14px; margin-bottom: 20px; }
    /* 表格樣式優化 */
    .stDataFrame { border: 1px solid #e0e0e0; border-radius: 10px; background-color: white; }
    /* 分頁標籤美化 */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #e1e4e8; border-radius: 8px 8px 0 0; padding: 10px 25px; font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background-color: #ffffff !important; color: #1e88e5 !important; }
    </style>
    """, unsafe_allow_html=True)

# 你的 54 隻股票清單
MY_TICKERS = [
    "AAPL", "NVDA", "TSLA", "GOOGL", "AMZN", "ONDS", "RCAT", "IONQ", "MP", "NBIS", 
    "CRWV", "APLD", "NVTS", "ALAB", "RKLD", "AVAV", "KTOS", "CRWD", "VRT", "PLTR", 
    "META", "RDDT", "RBLX", "SNOW", "SOUN", "SERV", "FIG", "APP", "ADBE", "TSM", 
    "AMD", "MRVL", "ORCL", "AVGO", "MU", "OKLO", "LEU", "VST", "NNE", "HIMS", 
    "TEM", "UNH", "OSCR", "SOFI", "HOOD", "CRCL", "JPM", "V", "UPST", "AEM", 
    "UBER", "NFLX", "EOSE", "BRK-B"
]

@st.cache_data(ttl=300)
def fetch_all_market_data(tickers):
    indices = ['SPY', 'QQQ', 'IWM']
    all_symbols = list(set(tickers + indices))
    data = yf.download(all_symbols, period='2y', progress=False)
    tz = pytz.timezone('Asia/Hong_Kong')
    sync_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    return data, sync_time

# 執行數據抓取
try:
    raw_data, sync_time = fetch_all_market_data(MY_TICKERS)
except:
    st.error("數據同步失敗，請檢查網路連線或稍後再試。")
    st.stop()

# --- 2. 頁面頭部 ---
st.markdown('<p class="main-title">🎯 NAT LIST</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sync-info"><b>SYNCED</b>: {sync_time} HKT | <b>DATA STATE</b>: LIVE YAHOO API</p>', unsafe_allow_html=True)

# --- 3. 核心分頁 ---
tab_watch, tab_etf, tab_sector = st.tabs(["📊 Watchlist", "📉 ETF Basis", "🧱 Sector View"])

# --- TAB 1: WATCHLIST (包含圖表) ---
with tab_watch:
    # 準備表格數據
    summary = []
    for t in MY_TICKERS:
        if t not in raw_data['Close'].columns: continue
        close_series = raw_data['Close'][t]
        spy_series = raw_data['Close']['SPY']
        
        price = close_series.iloc[-1]
        daily_change = (price / close_series.iloc[-2]) - 1
        
        # RS 計算
        rel_strength = close_series / spy_series
        rs_3m = (rel_strength.iloc[-1] / rel_strength.iloc[-63]) - 1
        rs_vs_spy = (price/close_series.iloc[-63]) - (spy_series.iloc[-1]/spy_series.iloc[-63])
        
        # VCP 簡單判斷
        vol_20d = close_series.iloc[-20:].std() / price
        vcp_status = "🎯 VCP" if vol_20d < 0.03 else "-"

        summary.append({
            "Symbol": t, "Price": price, "Daily %": daily_change,
            "RS (3M)": rs_3m, "RS vs SPY": rs_vs_spy, "VCP": vcp_status
        })
    
    df_main = pd.DataFrame(summary).sort_values("RS (3M)", ascending=False)

    # 顯示表格 (修正滾動與顏色)
    st.dataframe(
        df_main.style.format({
            "Price": "${:.2f}", "Daily %": "{:+.2%}", 
            "RS (3M)": "{:+.2%}", "RS vs SPY": "{:+.2%}"
        }).background_gradient(subset=["RS (3M)", "RS vs SPY"], cmap="RdYlGn", vmin=-0.15, vmax=0.15),
        use_container_width=True, height=450
    )

    st.markdown("---")
    
    # --- 重要：個股分析圖表區域 ---
    st.subheader("🔍 Technical Analysis Chart")
    
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1.5, 1])
    with col_ctrl1:
        selected_ticker = st.selectbox("Select Target", df_main['Symbol'].tolist(), index=0)
    with col_ctrl2:
        period = st.radio("Timeframe", ["3M", "6M", "1Y"], horizontal=True)
    with col_ctrl3:
        st.write("") # 垂直對齊
        tv_link = f"https://www.tradingview.com/chart/?symbol={selected_ticker}"
        st.link_button(f"🚀 OPEN {selected_ticker} IN TRADINGVIEW", tv_link, use_container_width=True)

    # 繪圖邏輯
    day_count = {"3M": 63, "6M": 126, "1Y": 252}[period]
    h = raw_data.xs(selected_ticker, axis=1, level=1).iloc[-day_count:]
    s = raw_data.xs('SPY', axis=1, level=1).iloc[-day_count:]
    
    # 
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.55, 0.15, 0.3]
    )

    # 1. K線圖
    fig.add_trace(go.Candlestick(
        x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], 
        name="Price", increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    ), row=1, col=1)
    
    # 2. 成交量
    vol_colors = ['#ef5350' if r['Open'] > r['Close'] else '#26a69a' for _, r in h.iterrows()]
    fig.add_trace(go.Bar(x=h.index, y=h['Volume'], name="Volume", marker_color=vol_colors, opacity=0.8), row=2, col=1)

    # 3. RS Line (相較於 SPY)
    rs_vals = (h['Close'] / s['Close'])
    fig.add_trace(go.Scatter(x=h.index, y=rs_vals, name="RS Line", line=dict(color='#00e676', width=2.5)), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", height=750, 
        xaxis_rangeslider_visible=False,
        margin=dict(l=40, r=40, t=20, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(type='date', tickformat='%b %d')

    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: ETF BASIS ---
with tab_etf:
    st.subheader("Global Market Context")
    idx_list = ['SPY', 'QQQ', 'IWM']
    idx_df = raw_data['Close'][idx_list].iloc[-126:] # 最近半年
    
    # 歸一化對比圖 (Base 100)
    fig_idx = go.Figure()
    for col in idx_df.columns:
        normalized = (idx_df[col] / idx_df[col].iloc[0]) * 100
        fig_idx.add_trace(go.Scatter(x=normalized.index, y=normalized, name=col))
    
    fig_idx.update_layout(title="Indices Performance (Last 6 Months, Base 100)", template="plotly_white", height=500)
    st.plotly_chart(fig_idx, use_container_width=True)

# --- TAB 3: SECTOR VIEW ---
with tab_sector:
    st.subheader("Relative Strength by Cluster")
    # 簡單根據你的清單做一個群組分類
    clusters = {
        "Semiconductors": ["NVDA", "TSM", "AMD", "AVGO", "MU", "ALAB"],
        "Big Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"],
        "SaaS/Security": ["CRWD", "PLTR", "SNOW", "ADBE", "ORCL", "APP"],
        "Energy/Defense": ["OKLO", "VST", "LEU", "NNE", "AVAV", "KTOS", "RCAT"]
    }
    
    cluster_perf = []
    for name, tickers in clusters.items():
        avg_rs = df_main[df_main['Symbol'].isin(tickers)]['RS (3M)'].mean()
        cluster_perf.append({"Cluster": name, "Avg RS (3M)": avg_rs})
    
    df_cluster = pd.DataFrame(cluster_perf).sort_values("Avg RS (3M)", ascending=False)
    
    fig_cluster = go.Figure(go.Bar(
        x=df_cluster['Avg RS (3M)'], y=df_cluster['Cluster'], orientation='h',
        marker_color=['#43a047' if x > 0 else '#e53935' for x in df_cluster['Avg RS (3M)']]
    ))
    fig_cluster.update_layout(title="Cluster Momentum", template="plotly_white")
    st.plotly_chart(fig_cluster, use_container_width=True)