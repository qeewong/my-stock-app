import streamlit as st
import pandas as pd
import yfinance as yf
import requests

# 將原本 Stockbot.txt 的翻譯地圖放入 (簡化版)
TRANSLATION_MAP = {
    "Electronic Technology": "電子科技", "Technology Services": "科技服務", 
    "Finance": "金融", "Semiconductors": "半導體"
}

# 這是你最核心的篩選邏輯，從 Stockbot.txt 移植過來 [cite: 40-43]
def fetch_tv_data(criteria_type):
    url = "https://scanner.tradingview.com/america/scan"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 基本門檻：價格>15, 市值>3億, 日成交量>50萬 [cite: 40]
    filters = [
        {"left": "close", "operation": "egreater", "right": 15},
        {"left": "market_cap_basic", "operation": "egreater", "right": 300000000},
        {"left": "volume", "operation": "egreater", "right": 500000},
    ]
    
    # 根據 Stockbot.txt 的不同策略加入均線條件 [cite: 40, 41]
    if criteria_type == 1: # 趨勢型 [cite: 40]
        filters.extend([{"left": "close", "operation": "egreater", "right": "SMA50"}, {"left": "SMA50", "operation": "egreater", "right": "SMA100"}])
    
    payload = {
        "filter": filters,
        "columns": ["name", "close", "change", "sector", "industry"],
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [0, 100]
    }
    
    resp = requests.post(url, json=payload, headers=headers)
    data = resp.json().get('data', [])
    
    results = []
    for item in data:
        row = item['d']
        results.append({
            "代號": item['s'], "名稱": row[0], "價格": row[1], 
            "漲跌幅": row[2]/100, "板塊": TRANSLATION_MAP.get(row[3], row[3])
        })
    return pd.DataFrame(results)

# --- Streamlit 網頁佈局 ---
st.title("🚀 我的專屬股票篩選網頁")

strat = st.selectbox("選擇篩選策略", [1, 2, 3], format_func=lambda x: ["趨勢動能型", "短線爆發型", "綜合嚴選型"][x-1])

if st.button("點我執行篩選"):
    with st.spinner('正在分析中...'):
        df = fetch_tv_data(strat)
        if not df.empty:
            st.success(f"找到 {len(df)} 檔符合條件的股票！")
            st.dataframe(df.style.format({"漲跌幅": "{:.2%}"}))
        else:
            st.warning("今日無符合條件股票")