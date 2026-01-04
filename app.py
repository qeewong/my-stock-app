import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(page_title="VCP & RS 專業交易終端", layout="wide")

# --- VCP 識別邏輯函數 ---
def detect_vcp(df_hist):
    """
    簡單 VCP 診斷：檢查最近 3 個波段的振幅是否遞減
    """
    # 獲取最近 60 天的高低點
    high_60 = df_hist['High'].rolling(60).max().iloc[-1]
    low_60 = df_hist['Low'].rolling(60).min().iloc[-1]
    total_depth = (high_60 - low_60) / high_60
    
    # 獲取最近 3 個 20 天周期的波動率 (ATR 簡化版)
    vol_1 = (df_hist['High'].iloc[-60:-40].max() - df_hist['Low'].iloc[-60:-40].min()) / df_hist['Close'].iloc[-40]
    vol_2 = (df_hist['High'].iloc[-40:-20].max() - df_hist['Low'].iloc[-40:-20].min()) / df_hist['Close'].iloc[-20]
    vol_3 = (df_hist['High'].iloc[-20:].max() - df_hist['Low'].iloc[-20:].min()) / df_hist['Close'].iloc[-1]
    
    # VCP 條件：波動收窄且價格接近高位
    is_vcp = vol_3 < vol_2 < vol_1 and df_hist['Close'].iloc[-1] > high_60 * 0.9
    
    status = "🎯 VCP FORMING" if is_vcp else "---"
    return status, round(vol_3 * 100, 2)

@st.cache_data(ttl=3600)
def fetch_vcp_data(tickers):
    all_symbols = tickers + ['SPY']
    df = yf.download(all_symbols, period='1y', progress=False)
    
    results = []
    for t in tickers:
        if t not in df['Close'].columns: continue
        
        t_data = df.xs(t, axis=1, level=1)
        vcp_status, curr_vol = detect_vcp(t_data)
        
        # RS 計算
        rel_perf = (df['Close'][t] / df['Close']['SPY'])
        rs_3m = (rel_perf.iloc[-1] / rel_perf.iloc[-63]) - 1
        
        results.append({
            "代號": t,
            "現價": t_data['Close'].iloc[-1],
            "VCP 診斷": vcp_status,
            "當前振幅(%)": curr_vol,
            "RS (3M)": rs_3m,
            "MA50": t_data['Close'].rolling(50).mean().iloc[-1]
        })
    return pd.DataFrame(results), df

# --- 介面佈局 ---
st.title("🧙‍♂️ VCP 形態與相對強弱監控")

tickers_input = st.sidebar.text_area("輸入代號", "NVDA, TSLA, AAPL, AMZN, META, MSFT, AMD, NFLX, SMCI, AVGO", height=150)
ticker_list = [t.strip().upper() for t in tickers_input.replace('\n', ',').split(',') if t.strip()]

df_summary, raw_data = fetch_vcp_data(ticker_list)

# 顯示看板
col_a, col_b = st.columns(2)
vcp_stocks = df_summary[df_summary['VCP 診斷'] == "🎯 VCP FORMING"]
col_a.metric("VCP 候選股數量", len(vcp_stocks))
col_b.write("💡 **VCP 提示：** 尋找振幅小於 5% 且 RS 強勁的標的。")

# --- 修正後的表格顯示代碼 ---
if not df_summary.empty:
    # 1. 確保數值列是正確的浮點數格式，防止渲染錯誤
    df_summary['RS (3M)'] = pd.to_numeric(df_summary['RS (3M)'], errors='coerce').fillna(0)
    df_summary['當前振幅(%)'] = pd.to_numeric(df_summary['當前振幅(%)'], errors='coerce').fillna(0)

    # 2. 使用更相容的表格美化寫法
    st.subheader("📋 實時狀態與排名")
    
    # 建立一個 Styler 對象
    styler = df_summary.style.format({
        "RS (3M)": "{:.2%}",
        "當前振幅(%)": "{:.2f}%",
        "現價": "{:.2f}",
        "MA50": "{:.2f}"
    })

    # 針對 VCP 診斷列進行條件高亮 (改用 applymap 以獲得更好的相容性)
    def highlight_vcp(val):
        color = '#1a472a' if val == "🎯 VCP FORMING" else ''
        return f'background-color: {color}'

    styler = styler.applymap(highlight_vcp, subset=['VCP 診斷'])
    
    # 加入 RS 的顏色漸變
    styler = styler.background_gradient(subset=["RS (3M)"], cmap="RdYlGn")

    st.dataframe(styler, use_container_width=True)

st.divider()

# 圖表詳細分析
target = st.selectbox("🎯 選擇個股查看 VCP 結構", df_summary['代號'].tolist())
hist = raw_data.xs(target, axis=1, level=1).iloc[-120:]

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

# K 線與均線
fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="K線"), row=1, col=1)
fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(50).mean(), name="50MA", line=dict(color='blue')), row=1, col=1)

# 成交量 (VCP 的關鍵是縮量)
fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name="成交量", marker_color='gray', opacity=0.5), row=2, col=1)

fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)