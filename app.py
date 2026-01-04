import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="自選股相對強弱分析", layout="wide")

# 側邊欄設定
st.sidebar.header("📊 設定中心")
default_tickers = "AAPL, MSFT, NVDA, TSLA, AMD, META, GOOGL, AMZN, NFLX, COIN, MSTR, LLY"
user_input = st.sidebar.text_area("請輸入股票代號 (用逗號或空格分隔)", default_tickers, height=150)

# 處理輸入的代號
ticker_list = [t.strip().upper() for t in user_input.replace('\n', ',').split(',') if t.strip()]

@st.cache_data(ttl=3600)
def fetch_rs_analysis(tickers):
    if not tickers: return pd.DataFrame(), None
    
    # 加入大盤 SPY 作為基準
    all_tickers = tickers + ['SPY']
    data = yf.download(all_tickers, period='1y', progress=False)['Close']
    
    # 如果只有一個股票或沒數據
    if data.empty: return pd.DataFrame(), None
    
    rs_results = []
    spy = data['SPY']
    
    for t in tickers:
        if t not in data.columns: continue
        
        # 核心 RS 公式：計算相對於 SPY 的表現
        # RS = (個股當前價 / 基準當前價) / (個股前期價 / 基準前期價) - 1
        curr_rel = data[t].iloc[-1] / spy.iloc[-1]
        
        # 1年、3個月、1個月的相對強弱
        rs_1y = (curr_rel / (data[t].iloc[0] / spy.iloc[0])) - 1
        rs_3m = (curr_rel / (data[t].iloc[-63] / spy.iloc[-63])) - 1
        rs_1m = (curr_rel / (data[t].iloc[-21] / spy.iloc[-21])) - 1
        
        # 當前價格與漲跌
        price = data[t].iloc[-1]
        change = (data[t].iloc[-1] / data[t].iloc[-2]) - 1
        
        rs_results.append({
            "代號": t,
            "最新價格": round(price, 2),
            "當日漲跌": change,
            "RS (1個月)": rs_1m,
            "RS (3個月)": rs_3m,
            "RS (1年)": rs_1y
        })
    
    df = pd.DataFrame(rs_results).sort_values("RS (3個月)", ascending=False)
    return df, data

# 獲取數據
df_rs, raw_data = fetch_rs_analysis(ticker_list)

# --- 網頁顯示介面 ---
st.title("📈 Relative Strength 分析儀表板")
st.markdown(f"**追蹤數量：{len(ticker_list)} 隻股票** | 基準指數：S&P 500 (SPY)")

if not df_rs.empty:
    # 第一部分：RS 排名表 (模仿網站表格)
    st.subheader("🏆 相對強弱排名 (RS Ranking)")
    # 使用漸變色顯示強弱
    st.dataframe(
        df_rs.style.format({
            "當日漲跌": "{:.2%}", "RS (1個月)": "{:.2%}", 
            "RS (3個月)": "{:.2%}", "RS (1年)": "{:.2%}"
        }).background_gradient(subset=["RS (3個月)", "RS (1個月)"], cmap="RdYlGn"),
        use_container_width=True,
        height=400
    )

    # 第二部分：圖表分析
    st.divider()
    col_sel, col_chart = st.columns([1, 3])
    
    with col_sel:
        st.subheader("🔍 單個詳細分析")
        target = st.selectbox("選擇股票查看 RS Line", df_rs['代號'].tolist())
        
        # 顯示該股數據指標
        row = df_rs[df_rs['代號'] == target].iloc[0]
        st.metric("當前 RS (3M)", f"{row['RS (3個月)']:.2%}")
        st.write("---")
        st.caption("💡 RS Line 向上代表表現跑贏大盤，向下代表跑輸。")

    with col_chart:
        # 繪製 RS Line (個股價格 / SPY 價格)
        rs_line_data = (raw_data[target] / raw_data['SPY'])
        # 歸一化（讓圖表從 100 開始看起，比較直觀）
        rs_line_normalized = (rs_line_data / rs_line_data.iloc[0]) * 100
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=rs_line_normalized.index, 
            y=rs_line_normalized, 
            name="RS Line (vs SPY)", 
            line=dict(color='#00FF00', width=2)
        ))
        
        fig.update_layout(
            title=f"{target} 的相對強弱曲線 (RS Line)",
            xaxis_title="日期",
            yaxis_title="強弱指數 (100 為起點)",
            template="plotly_dark",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("請在左側輸入正確的股票代號以開始分析。")