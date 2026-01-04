import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 網頁配置 ---
st.set_page_config(page_title="RS & VCP 專業監控", layout="wide")

# --- 1. 你的自選股票清單 ---
MY_TICKERS = [
    "AAPL", "NVDA", "TSLA", "GOOGL", "AMZN", "ONDS", "RCAT", "IONQ", "MP", "NBIS", 
    "CRWV", "APLD", "NVTS", "ALAB", "RKLD", "AVAV", "KTOS", "CRWD", "VRT", "PLTR", 
    "META", "RDDT", "RBLX", "SNOW", "SOUN", "SERV", "FIG", "APP", "ADBE", "TSM", 
    "AMD", "MRVL", "ORCL", "AVGO", "MU", "OKLO", "LEU", "VST", "NNE", "HIMS", 
    "TEM", "UNH", "OSCR", "SOFI", "HOOD", "CRCL", "JPM", "V", "UPST", "AEM", 
    "UBER", "NFLX", "EOSE", "BRK-B"
]

SECTOR_MAP = {
    "Technology": "電子科技", "Communication Services": "通訊服務",
    "Consumer Cyclical": "週期性消費", "Financial Services": "金融服務",
    "Healthcare": "醫療保健", "Energy": "能源", "Industrials": "工業",
    "Basic Materials": "基礎材料", "Utilities": "公共事業", "Real Estate": "房地產"
}

# --- 2. 核心功能函數 ---
@st.cache_data(ttl=3600)
def fetch_everything(tickers):
    all_symbols = tickers + ['SPY']
    data = yf.download(all_symbols, period='1y', progress=False)
    close_df = data['Close']
    
    summary_list = []
    for t in tickers:
        if t not in close_df.columns: continue
        
        # 指標計算
        ma10 = close_df[t].rolling(10).mean().iloc[-1]
        ma50 = close_df[t].rolling(50).mean().iloc[-1]
        rel_perf = (close_df[t] / close_df['SPY'])
        rs_3m = (rel_perf.iloc[-1] / rel_perf.iloc[-63]) - 1
        
        try:
            info = yf.Ticker(t).info
            sector = SECTOR_MAP.get(info.get('sector', 'Unknown'), info.get('sector', '其他'))
        except:
            sector = "未知"

        summary_list.append({
            "代號": t, "板塊": sector, "現價": close_df[t].iloc[-1],
            "今日漲跌": (close_df[t].iloc[-1] / close_df[t].iloc[-2]) - 1,
            "RS (3M)": rs_3m, "MA10": ma10, "MA50": ma50,
            "VCP診斷": "🎯 VCP" if (rs_3m > 0 and close_df[t].iloc[-1] > ma50) else "---"
        })
    
    return pd.DataFrame(summary_list), data

# --- 3. 網頁渲染 ---
st.title("🏹 個人強勢股 & 板塊監控終端")

with st.spinner('正在同步市場數據...'):
    df_summary, raw_data = fetch_everything(MY_TICKERS)

# --- A. 板塊強度統計圖 ---
st.subheader("📊 板塊平均相對強度 (RS)")
sector_perf = df_summary.groupby("板塊")["RS (3M)"].mean().sort_values(ascending=True)
fig_sector = go.Figure(go.Bar(
    x=sector_perf.values, y=sector_perf.index, orientation='h',
    marker_color=['#00ff00' if x > 0 else '#ff4b4b' for x in sector_perf.values]
))
fig_sector.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig_sector, use_container_width=True)

# --- B. 數據表格 (修復後的 Styler) ---
st.subheader("📋 實時排名與狀態")
st.dataframe(
    df_summary.style.format({"今日漲跌": "{:.2%}", "RS (3M)": "{:.2%}", "現價": "{:.2f}"})
    .background_gradient(subset=["RS (3M)"], cmap="RdYlGn"),
    use_container_width=True
)

st.divider()

# --- C. 詳細圖表與 TradingView 跳轉 ---
target = st.selectbox("🎯 選擇分析對象", df_summary['代號'].tolist())

# 加入 TradingView 跳轉按鈕
tv_url = f"https://www.tradingview.com/chart/?symbol={target}"
st.link_button(f"🚀 在 TradingView 開啟 {target} 圖表", tv_url, use_container_width=True)

# 圖表繪製
hist = raw_data.xs(target, axis=1, level=1).iloc[-120:]
hist_spy = raw_data.xs('SPY', axis=1, level=1).iloc[-120:]

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.3])

fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="K線"), row=1, col=1)
fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(10).mean(), name="MA10", line=dict(color='yellow', width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(50).mean(), name="MA50", line=dict(color='blue', width=1)), row=1, col=1)

colors = ['red' if row['Open'] > row['Close'] else 'green' for index, row in hist.iterrows()]
fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name="成交量", marker_color=colors), row=2, col=1)

rs_vals = (hist['Close'] / hist_spy['Close'])
fig.add_trace(go.Scatter(x=hist.index, y=rs_vals, name="RS Line", line=dict(color='#00ff00', width=2)), row=3, col=1)

fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False, showlegend=False)
st.plotly_chart(fig, use_container_width=True)