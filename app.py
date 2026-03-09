import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="成功消防大隊 - 體技能儀表板", page_icon="🚒", layout="wide")
st.title("🚒 成功消防大隊 - 體技能成績分析看板")

# --- 2. 串接 Google Sheets 資料 ---
# ⚠️ 請把下面這串網址，換成你剛剛在「第一步」複製的 Google Sheets CSV 網址
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQZVbsBMLdNws_DwHxVBuhc7VaA8oNdOakUmXfE28USGAhKhp1f1ni23kWrhBOESPg70Dr-fwYLYGfH/pub?gid=0&single=true&output=csv" 

# 使用 @st.cache_data 可以讓資料暫存，不用每次點擊都重新下載，提升網頁速度 (ttl=60代表每60秒才更新一次)
@st.cache_data(ttl=60)
def load_data(url):
    df = pd.read_csv(url)
    return df

try:
    # 載入資料
    df = load_data(sheet_url)
    
    # --- 3. 介面與資料展示 ---
    st.success("✅ 成功連線至 Google Sheets 資料庫！")
    
    # 顯示原始資料表 (加上展開折疊功能，讓畫面更乾淨)
    with st.expander("👀 點我查看/隱藏原始成績單"):
        st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # --- 4. 畫出第一張圖表：各分隊引體向上平均成績 ---
    st.subheader("📊 各分隊【引體向上】平均成績比較")
    
    # 用 Pandas 計算各分隊的平均值，並重置索引
    avg_pullups = df.groupby('分隊')['引體向上_下'].mean().reset_index()
    avg_pullups = avg_pullups.rename(columns={'引體向上_下': '平均次數'})

    # 用 Plotly 畫長條圖
    fig = px.bar(
        avg_pullups, 
        x='分隊', 
        y='平均次數', 
        color='分隊', # 依分隊給不同顏色
        text_auto='.1f', # 顯示小數點後1位的數字
        title="各分隊引體向上平均次數"
    )
    
    # 在網頁上顯示圖表
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"連線失敗，請確認你的網址是否有貼對，並已經『發布到網路』。錯誤訊息：{e}")
