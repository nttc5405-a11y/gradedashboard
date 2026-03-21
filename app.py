import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="成功消防大隊 - 戰情室 3.0", page_icon="🚒", layout="wide")

# 強制自訂 CSS 樣式
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 18px; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能戰情室 3.0 (測驗表同步版)")

# --- 根據圖片定義欄位結構 ---
# 基本資料
BASE_COLS = ['測驗日期', '分隊', '姓名', '性別', '年齡']

# 體能項目 (40%)
PHYSICAL_METRICS = [
    '立定跳遠', '後拋擲遠', '6公尺30秒折返跑', 
    '菱形槓硬舉', '懸吊屈體', '負重行走', '1500公尺跑走'
]

# 技能項目 (60%)
SKILL_METRICS = [
    '結索能力', '繩索登降', '固定點架設', 
    '滑輪拖拉架設', '緊繃繩系統架設'
]

# 總分項目
TOTAL_METRICS = ['體能合計40%', '技能合計60%', '總成績']

@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        df = pd.read_csv(url)
        
        # 處理「分數部分在奇數列」的邏輯：
        # 如果你的 CSV 結構是 [項目1_紀錄, 項目1_分數, 項目2_紀錄, 項目2_分數...]
        # 我們通常會分析「分數」來做圖表，分析「紀錄」來查看個人細節
        
        all_cols = df.columns.tolist()
        
        # 將所有數值欄位轉為數字
        numeric_cols = [c for c in all_cols if c not in BASE_COLS]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 新增年齡層
        bins = [20, 30, 40, 50, 70]
        labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
        df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        
        return df, numeric_cols
    except Exception as e:
        st.error(f"資料讀取失敗：{e}")
        return None, []

df, all_metrics = load_and_clean_data()

if df is not None:
    # 這裡自動偵測你的 CSV 中哪些是「分數」欄位
    # 假設分數欄位名稱包含 "分數" 字樣，或你提到的奇數索引邏輯
    score_metrics = [m for m in all_metrics if "分數" in m or "合計" in m or "成績" in m]
    if not score_metrics: # 如果 CSV 沒寫分數兩字，就用全部項目
        score_metrics = all_metrics

    all_dates = sorted(df['測驗日期'].unique(), reverse=True)
    latest_date = all_dates[0]
    
    # 頂部 Kpi
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("本次測驗總人數", f"{len(df[df['測驗日期']==latest_date])} 人")
    with k2: 
        top_scorer = df[df['測驗日期']==latest_date].sort_values(by='總成績', ascending=False).iloc[0]
        st.metric("本次最高分", f"{top_scorer['總成績']}", f"🏆 {top_scorer['姓名']}")
    with k3: st.metric("受測分隊數", f"{df['分隊'].nunique()} 個")
    with k4: st.metric("最新測驗日期", f"{latest_date}")

    tab_overview, tab_group, tab_individual, tab_alert = st.tabs([
        "📊 戰情總覽", "🔍 交叉分析", "🎯 個人雷達", "🚨 警示名單"
    ])

    # --- Tab 1: 大隊戰情總覽 ---
    with tab_overview:
        selected_metric = st.selectbox("請選擇觀測指標（分數）：", score_metrics)
        
        c1, c2 = st.columns(2)
        with c1:
            latest_df = df[df['測驗日期'] == latest_date]
            avg_df = latest_df.groupby('分隊')[selected_metric].mean().reset_index()
            fig_bar = px.bar(avg_df, x='分隊', y=selected_metric, color='分隊', text_auto='.1f', 
                             title=f"各分隊 {selected_metric} 平均表現")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            trend_df = df.groupby('測驗日期')[selected_metric].mean().reset_index()
            fig_line = px.line(trend_df, x='測驗日期', y=selected_metric, markers=True, title=f"大隊 {selected_metric} 歷次趨勢")
            st.plotly_chart(fig_line, use_container_width=True)

    # --- Tab 3: 個人雷達圖 (依照圖片區分體能與技能) ---
    with tab_individual:
        p_name = st.selectbox("選擇隊員", df['姓名'].unique())
        p_latest = df[(df['姓名'] == p_name) & (df['測驗日期'] == latest_date)].iloc[0]
        
        col_info, col_radar = st.columns([1, 2])
        with col_info:
            st.info(f"**{p_latest['姓名']}** ({p_latest['分隊']})")
            st.write(f"🔹 **總成績：{p_latest['總成績']}**")
            st.write(f"🔹 體能合計(40%)：{p_latest.get('體能合計40%', 'N/A')}")
            st.write(f"🔹 技能合計(60%)：{p_latest.get('技能合計60%', 'N/A')}")
            
            # 顯示具體數值表格
            st.write("---")
            st.write("**測驗原始紀錄：**")
            # 這裡你可以手動列出圖片中對應的紀錄欄位
            display_items = [m for m in PHYSICAL_METRICS + SKILL_METRICS if m in df.columns]
            st.dataframe(pd.DataFrame(p_latest[display_items]).T)

        with col_radar:
            # 製作雷達圖（使用分數欄位）
            # 找出與測驗項目對應的分數欄位
            radar_cols = [c for c in score_metrics if any(m in c for m in PHYSICAL_METRICS + SKILL_METRICS)]
            
            if radar_cols:
                radar_data = pd.DataFrame({
                    '項目': radar_cols,
                    '得分': [p_latest[c] for c in radar_cols]
                })
                fig_radar = px.line_polar(radar_data, r='得分', theta='項目', line_close=True)
                fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
                fig_radar.update_layout(title=f"{p_name} 體技能分佈")
                st.plotly_chart(fig_radar, use_container_width=True)

else:
    st.info("請確認資料庫已正確連線並包含「體能合計40%」、「技能合計60%」等欄位。")
