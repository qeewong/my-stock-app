import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 1. 頁面配置 ---
st.set_page_config(page_title="Spring Stock Strength Clone", layout="wide")

# 自定義 CSS 模仿圖片中的乾淨風格
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #1e1e1e; }
    .status-tag { 
        font-size: 10px; padding: 2px 6px; border-radius: 4px; 
        margin-left: 5px; font-weight: bold; text-transform: uppercase;
    }
    .vcp-tag { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #2e7d32; }
    .updated-text { text-align: right; color: #666; font-size: 12px; margin-bottom: 5px; }
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

# --- 2. 數據核心 ---
@st.cache_data(ttl=300) # 每5分鐘更新一次
def fetch_data(tickers):
    all_symbols = tickers + ['SPY']
    data = yf.download(all_symbols, period='2y', progress=False)
    close_df = data['Close']
    
    summary = []
    for t in tickers:
        if t not in close_df.columns: continue
        
        # 指標計算
        price = close_df[t].iloc[-1]
        prev_price = close_df[t].iloc[-2]
        change = (price / prev_price) - 1
        
        # RS (3M) & RS vs SPY
        rel = close_df[t] / close_df['SPY']
        rs_3m = (rel.iloc[-1] / rel.iloc[-63]) - 1
        rs_vs_spy = (price / close_df[t].iloc[-63]) - (close_df['SPY'].iloc[-1] / close_df['SPY'].iloc[-63])
        
        # VCP 簡單邏輯：波動收窄且站穩 50MA
        ma50 = close_df[t].rolling(50).mean().iloc[-1]
        vol_20 = (close_df[t].iloc[-20:].max() - close_df[t].iloc[-20:].min()) / price
        is_vcp = "🎯 VCP" if (vol_20 < 0.15 and price > ma50) else ""
        
        summary.append({
            "Symbol": t,
            "Price": price,
            "Daily Change": change,
            "RS (3M)": rs_3m,
            "RS vs SPY": rs_vs_spy,
            "VCP": is_vcp
        })
    
    # 獲取最新更新時間
    tz = pytz.timezone('Asia/Hong_Kong')
    update_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    return pd.DataFrame(summary), data, update_time

# --- 3. 畫面執行 ---
df_summary, raw_data, last_update = fetch_data(MY_TICKERS)

# 右上角時間
st.markdown(f'<p class="updated-text">UPDATED: {last_update} (HKT)</p>', unsafe_allow_html=True)

# --- A. 模仿圖片的表格佈局 ---
st.subheader("Technical Analysis View")

# 按 RS (3M) 排序
df_display = df_summary.sort_values("RS (3M)", ascending=False)

# 表格顯示
st.dataframe(
    df_display.style.format({
        "Price": "${:.2f}",
        "Daily Change": "{:+.2%}",
        "RS (3M)": "{:+.2%}",
        "RS vs SPY": "{:+.2%}"
    }).background_gradient(subset=["RS (3M)", "RS vs SPY"], cmap="RdYlGn"),
    use_container_width=True,
    height=600
)

st.divider()

# --- B. 專業對比圖表 ---
col1, col2 = st.columns([1, 1])
with col1:
    target = st.selectbox("Select Symbol", df_display['Symbol'].tolist())
with col2:
    time_frame = st.radio("Range", ["3M", "6M", "1Y"], horizontal=True, index=0)

# 時間切換邏輯
days_map = {"3M": 63, "6M": 126, "1Y": 252}
days = days_map[time_frame]

# 數據準備
h = raw_data.xs(target, axis=1, level=1).iloc[-days:]
s = raw_data.xs('SPY', axis=1, level=1).iloc[-days:]

# 建立圖表 (K線 + 成交量 + RS Line)
fig = make_subplots(
    rows=3, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.03, 
    row_heights=[0.6, 0.15, 0.25],
    subplot_titles=(f"{target} Candlestick", "Volume", "RS Line (Relative Strength)")
)

# 1. K線圖
fig.add_trace(go.Candlestick(
    x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], 
    name="Price"
), row=1, col=1)

# 2. 成交量
colors = ['#ef5350' if r['Open'] > r['Close'] else '#26a69a' for _, r in h.iterrows()]
fig.add_trace(go.Bar(x=h.index, y=h['Volume'], name="Volume", marker_color=colors), row=2, col=1)

# 3. RS Line
rs_line = (h['Close'] / s['Close'])
fig.add_trace(go.Scatter(x=h.index, y=rs_line, name="RS vs SPY", line=dict(color='#39FF14', width=2)), row=3, col=1)

# 佈局與日期設定
fig.update_layout(
    template="plotly_dark", height=800, 
    xaxis_rangeslider_visible=False,
    margin=dict(l=40, r=40, t=40, b=40),
    hovermode="x unified"
)
fig.update_xaxes(type='date', tickformat='%b %d, %Y', row=3, col=1) # 顯示日期與年份

st.plotly_chart(fig, use_container_width=True)

# TradingView 跳轉按鈕
st.link_button(f"Open {target} on TradingView", f"https://www.tradingview.com/chart/?symbol={target}", use_container_width=True)