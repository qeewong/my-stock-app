import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 網頁基礎配置 ---
st.set_page_config(page_title="專業強勢股監控", layout="wide")

# 你的 54 隻自選股票清單
MY_TICKERS = [
    "AAPL", "NVDA", "TSLA", "GOOGL", "AMZN", "ONDS", "RCAT", "IONQ", "MP", "NBIS", 
    "CRWV", "APLD", "NVTS", "ALAB", "RKLD", "AVAV", "KTOS", "CRWD", "VRT", "PLTR", 
    "META", "RDDT", "RBLX", "SNOW", "SOUN", "SERV", "FIG", "APP", "ADBE", "TSM", 
    "AMD", "MRVL", "ORCL", "AVGO", "MU", "OKLO", "LEU", "VST", "NNE", "HIMS", 
    "TEM", "UNH", "OSCR", "SOFI", "HOOD", "CRCL", "JPM", "V", "UPST", "AEM", 
    "UBER", "NFLX", "EOSE", "BRK-B"
]

# --- 2. 數據獲取核心 ---
@st.cache_data(ttl=3600)
def fetch_market_data(tickers):
    all_symbols = tickers + ['SPY']
    # 抓取 1.5 年數據以確保均線計算和時間切換正常
    data = yf.download(all_symbols, period='2y', progress=False)
    close_df = data['Close']
    
    summary = []
    for t in tickers:
        if t not in close_df.columns: continue
        last_p = close_df[t].iloc[-1]
        change = (last_p / close_df[t].iloc[-2]) - 1
        
        # RS 計算 (相對 SPY 的 3個月變動)
        rel = close_df[t] / close_df['SPY']
        rs_3m = (rel.iloc[-1] / rel.iloc[-63]) - 1
        
        summary.append({
            "代號": t,
            "現價": last_p,
            "今日漲跌": change,
            "RS (3M)": rs_3m,
            "MA20": close_df[t].rolling(20).mean().iloc[-1],
            "MA50": close_df[t].rolling(50).mean().iloc[-1]
        })
    return pd.DataFrame(summary), data

# --- 3. 畫面構建 ---
st.title("🏹 專業級強勢股 RS 監控終端")

with st.spinner('同步市場數據中...'):
    df_summary, raw_data = fetch_market_data(MY_TICKERS)

# --- A. 數據表格 (最大化顯示) ---
st.subheader("📋 實時市場排名 (按 RS 強度排序)")
df_display = df_summary.sort_values("RS (3M)", ascending=False)

st.dataframe(
    df_display.style.format({
        "今日漲跌": "{:.2%}", "RS (3M)": "{:.2%}", 
        "現價": "{:.2f}", "MA20": "{:.2f}", "MA50": "{:.2f}"
    }).background_gradient(subset=["RS (3M)"], cmap="RdYlGn"),
    use_container_width=True,
    height=800 # 這裡設高，方便看 20 隻以上
)

st.divider()

# --- B. 圖表區域 (修復比例與日期) ---
st.subheader("📈 個股詳細對比分析")
col_sel, col_btn = st.columns([1, 1])
with col_sel:
    target = st.selectbox("選擇股票", df_display['代號'].tolist())
with col_btn:
    # 重新加入時間切換
    period_choice = st.radio("時間範圍", ["3個月", "6個月", "1年"], horizontal=True)

# 根據選擇過濾數據
days_map = {"3個月": 63, "6個月": 126, "1年": 252}
view_days = days_map[period_choice]

hist = raw_data.xs(target, axis=1, level=1).iloc[-view_days:]
spy_hist = raw_data.xs('SPY', axis=1, level=1).iloc[-view_days:]

# 建立圖表 (修正比例：0.6, 0.15, 0.25)
fig = make_subplots(
    rows=3, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.03, 
    row_heights=[0.6, 0.15, 0.25]
)

# 1. K線與均線 (修正顏色與線寬)
fig.add_trace(go.Candlestick(
    x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], 
    name="K線", increasing_line_color='#00ff00', decreasing_line_color='#ff4b4b'
), row=1, col=1)
fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(10).mean(), name="MA10", line=dict(color='yellow', width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(50).mean(), name="MA50", line=dict(color='#00d4ff', width=1.5)), row=1, col=1)

# 2. 成交量
v_colors = ['#ff4b4b' if r['Open'] > r['Close'] else '#00ff00' for _, r in hist.iterrows()]
fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name="成交量", marker_color=v_colors, opacity=0.8), row=2, col=1)

# 3. RS Line (補上日期座標)
rs_line = (hist['Close'] / spy_hist['Close'])
fig.add_trace(go.Scatter(x=hist.index, y=rs_line, name="RS Line", line=dict(color='#39FF14', width=2.5)), row=3, col=1)

# 全域佈局優化
fig.update_layout(
    template="plotly_dark", 
    height=850, 
    xaxis_rangeslider_visible=False,
    margin=dict(l=50, r=50, t=30, b=50),
    hovermode="x unified"
)

# 強制顯示日期格式
fig.update_xaxes(type='date', tickformat='%Y-%m', row=3, col=1)

st.plotly_chart(fig, use_container_width=True)

# TradingView 快捷鍵
st.link_button(f"🚀 開啟 TradingView 詳細看盤 ({target})", f"https://www.tradingview.com/chart/?symbol={target}", use_container_width=True)