import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# 網頁基礎設定
st.set_page_config(page_title="RS Elite Dashboard", layout="wide")

# 自定義 CSS：打造深色專業介面
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { color: #00FF00; }
    .stDataFrame { border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ 專業級股票相對強弱 (RS) 監控系統")

# 側邊欄：自選股輸入
st.sidebar.header("📋 我的自選清單")
default_list = "NVDA, TSLA, AAPL, MSFT, AMD, AMZN, META, GOOGL, NFLX, SMCI"
ticker_input = st.sidebar.text_area("輸入代號 (逗號分隔)", default_list, height=150)
ticker_list = [t.strip().upper() for t in ticker_input.replace('\n', ',').split(',') if t.strip()]

@st.cache_data(ttl=3600)
def get_advanced_data(tickers):
    # 抓取 1 年數據用於計算
    all_symbols = tickers + ['SPY']
    df = yf.download(all_symbols, period='1y', progress=False)['Close']
    
    results = []
    for t in tickers:
        if t not in df.columns: continue
        # 計算 RS 分數 (基於當前 vs 基準)
        rel_perf = (df[t] / df['SPY'])
        rs_score = (rel_perf.iloc[-1] / rel_perf.iloc[-63]) - 1 # 3個月相對強弱
        
        results.append({
            "代號": t,
            "現價": df[t].iloc[-1],
            "今日漲跌": (df[t].iloc[-1] / df[t].iloc[-2]) - 1,
            "RS強弱值": rs_score,
            "距52週高位": (df[t].iloc[-1] / df[t].max()) - 1
        })
    return pd.DataFrame(results).sort_values("RS強弱值", ascending=False), df

df_res, raw_data = get_advanced_data(ticker_list)

# 第一部分：RS 排名列表
st.subheader("📊 相對強度排名 (基於 SPY 基準)")
st.dataframe(
    df_res.style.format({
        "現價": "{:.2f}", "今日漲跌": "{:.2%}", 
        "RS強弱值": "{:.2%}", "距52週高位": "{:.2%}"
    }).background_gradient(subset=["RS強弱值"], cmap="RdYlGn"),
    use_container_width=True
)

st.divider()

# 第二部分：一模一樣的高低比較圖 (Normalization)
st.subheader("📉 價格走勢與 SPY 即時對比 (歸一化)")
selected_stock = st.selectbox("選擇要對比的股票", df_res['代號'].tolist())

# 時間範圍選擇
period = st.radio("時間範圍", ["3個月", "6個月", "1年"], horizontal=True)
days = {"3個月": 63, "6個月": 126, "1年": 252}[period]

# 準備對比數據：將起點設為 100
stock_series = raw_data[selected_stock].iloc[-days:]
spy_series = raw_data['SPY'].iloc[-days:]

norm_stock = (stock_series / stock_series.iloc[0]) * 100
norm_spy = (spy_series / spy_series.iloc[0]) * 100
rs_line = (stock_series / spy_series) / (stock_series.iloc[0] / spy_series.iloc[0]) * 100

# 建立雙軸圖表
fig = make_subplots(specs=[[{"secondary_y": True}]])

# 1. 股票走勢 (藍色)
fig.add_trace(go.Scatter(x=norm_stock.index, y=norm_stock, name=f"{selected_stock} (歸一化)", 
                         line=dict(color='#00D4FF', width=3)), secondary_y=False)

# 2. SPY 走勢 (橘色/灰色)
fig.add_trace(go.Scatter(x=norm_spy.index, y=norm_spy, name="S&P 500 (SPY)", 
                         line=dict(color='#FFBB00', width=2, dash='dot')), secondary_y=False)

# 3. RS Line (螢光綠) - 這是最重要的指標
fig.add_trace(go.Scatter(x=rs_line.index, y=rs_line, name="RS Line (強弱線)", 
                         line=dict(color='#00FF00', width=2)), secondary_y=True)

fig.update_layout(
    template="plotly_dark",
    height=600,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

fig.update_yaxes(title_text="價格指數 (起點=100)", secondary_y=False)
fig.update_yaxes(title_text="RS 強度比率", secondary_y=True, showgrid=False)

st.plotly_chart(fig, use_container_width=True)

st.caption("💡 解讀：當藍線在黃線上方，代表該股跑贏大盤；當綠色 RS Line 向上爬升，代表強度增加。")