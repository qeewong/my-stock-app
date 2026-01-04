import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="專業 RS 交易終端", layout="wide")

# --- 自定義風格 ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #e1e4e8; }
    .status-strong { color: #00ff00; font-weight: bold; border: 1px solid #00ff00; padding: 2px 5px; border-radius: 3px; }
    .status-bear { color: #ff4b4b; font-weight: bold; border: 1px solid #ff4b4b; padding: 2px 5px; border-radius: 3px; }
    </style>
    """, unsafe_allow_html=True)

# --- 功能函數 ---
def get_status(row):
    # 簡單邏輯判定狀態
    if row['RS (3M)'] > 0.05 and row['現價'] > row['MA50']:
        return "🔥 VERY STRONG"
    elif row['現價'] < row['MA20'] and row['RS (3M)'] < 0:
        return "🐻 TURNING BEAR"
    elif row['現價'] > row['MA10']:
        return "📈 BULLISH"
    else:
        return "⚖️ NEUTRAL"

@st.cache_data(ttl=3600)
def fetch_full_data(tickers):
    all_symbols = tickers + ['SPY']
    # 抓取足夠計算 50MA 的數據
    df = yf.download(all_symbols, period='1y', progress=False)
    close_df = df['Close']
    
    results = []
    for t in tickers:
        if t not in close_df.columns: continue
        # 計算均線
        ma10 = close_df[t].rolling(10).mean().iloc[-1]
        ma20 = close_df[t].rolling(20).mean().iloc[-1]
        ma50 = close_df[t].rolling(50).mean().iloc[-1]
        
        # 相對強弱
        rel_perf = (close_df[t] / close_df['SPY'])
        rs_3m = (rel_perf.iloc[-1] / rel_perf.iloc[-63]) - 1
        
        results.append({
            "代號": t, "現價": close_df[t].iloc[-1],
            "MA10": ma10, "MA20": ma20, "MA50": ma50,
            "RS (3M)": rs_3m,
            "今日漲跌": (close_df[t].iloc[-1] / close_df[t].iloc[-2]) - 1
        })
    
    status_df = pd.DataFrame(results)
    status_df['狀態'] = status_df.apply(get_status, axis=1)
    return status_df, df

# --- 側邊欄與數據載入 ---
st.sidebar.title("🛠️ 控制台")
tickers_input = st.sidebar.text_area("輸入代號", "NVDA, TSLA, AAPL, AMZN, META, MSFT, AMD, GOOGL", height=200)
ticker_list = [t.strip().upper() for t in tickers_input.replace('\n', ',').split(',') if t.strip()]

df_summary, raw_data = fetch_full_data(ticker_list)
s
# --- 介面佈局 ---
st.title("🚀 RS Elite Market Scanner")

# --- B. 數據表格 (加入點擊跳轉功能) ---
st.subheader("📋 實時排名與狀態 (點擊代號開啟 TradingView)")

# 建立跳轉連結的函式
def make_clickable(ticker):
    # TradingView 的標準跳轉網址
    url = f"https://www.tradingview.com/chart/?symbol={ticker}"
    return f'<a href="{url}" target="_blank">{ticker}</a>'

# 複製一份表格用作顯示
df_display = df_summary.copy()

# 將代號欄位轉換為 HTML 連結
df_display['代號'] = df_display['代號'].apply(make_clickable)

# 使用 st.write + to_html 來渲染含連結的表格
st.write(
    df_display.style.format({
        "今日漲跌": "{:.2%}", 
        "RS (3M)": "{:.2%}", 
        "現價": "{:.2f}"
    })
    .background_gradient(subset=["RS (3M)"], cmap="RdYlGn")
    .to_html(escape=False, index=False), 
    unsafe_allow_html=True
)

st.write("") # 增加一點間距

# 圖表區
col1, col2 = st.columns([1, 3])
with col1:
    target = st.selectbox("🎯 選擇分析對象", df_summary['代號'].tolist())
    target_info = df_summary[df_summary['代號'] == target].iloc[0]
    st.metric("當前狀態", target_info['狀態'])
    st.write(f"**MA10:** {target_info['MA10']:.2f}")
    st.write(f"**MA20:** {target_info['MA20']:.2f}")
    st.write(f"**MA50:** {target_info['MA50']:.2f}")

with col2:
    # 準備 K 線數據
    hist = raw_data.xs(target, axis=1, level=1).iloc[-100:] # 取最近100天
    hist_spy = raw_data.xs('SPY', axis=1, level=1).iloc[-100:]
    
    # 建立多子圖 (K線 + RS Line)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # 1. 蠟燭圖 (Candlestick)
    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist['Open'], high=hist['High'],
        low=hist['Low'], close=hist['Close'], name=f"{target} 價格"
    ), row=1, col=1)

    # 2. 加入均線
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(10).mean(), name="MA10", line=dict(color='yellow', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(20).mean(), name="MA20", line=dict(color='orange', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(50).mean(), name="MA50", line=dict(color='blue', width=1)), row=1, col=1)

    # 3. RS Line (相對於 SPY)
    rs_vals = (hist['Close'] / hist_spy['Close'])
    fig.add_trace(go.Scatter(x=hist.index, y=rs_vals, name="RS Line", line=dict(color='#00ff00', width=2)), row=2, col=1)

    fig.update_layout(template="plotly_dark", height=700, showlegend=True,
                      xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)