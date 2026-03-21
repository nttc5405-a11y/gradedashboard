import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 頁面基本設定 ---
st.set_page_config(page_title="成功消防大隊 - 戰情室 3.0", page_icon="🚒", layout="wide")

# 自訂 CSS 樣式
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 18px; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能戰情室 3.0 (自動合併修正版)")

# --- 1. 資料讀取與清洗邏輯 ---
@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        # 修正處：正確指令是 pd.read_csv
        raw_df = pd.read_csv(url)
        
        # 移除全空行
        raw_df = raw_df.dropna(subset=['單位'], how='all').reset_index(drop=True)

        # 分離「紀錄列」與「分數列」
        # 偶數索引 (0, 2...) 是紀錄，奇數索引 (1, 3...) 是分數
        data_rows = raw_df.iloc[::2].reset_index(drop=True)
        score_rows = raw_df.iloc[1::2].reset_index(drop=True)

        # 基本資料欄位
        base_info_cols = ['NO.', '單位', '姓名', '性別', '年齡']
        
        # 處理紀錄列：將測驗項目加上 "_紀錄" 避免與分數欄位衝突
        data_cols_renamed = {}
        for col in data_rows.columns:
            if col not in base_info_cols and '備註' not in col and '名次' not in col:
                data_cols_renamed[col] = f"{col}_紀錄"
        data_rows = data_rows.rename(columns=data_cols_renamed)

        # 處理分數列：只拿走分數數值，基本資料用紀錄列的就好
        score_cols = [c for c in score_rows.columns if c not in base_info_cols]
        score_rows_subset = score_rows[score_cols]

        # 橫向合併 (紀錄 + 分數)
        df = pd.concat([data_rows, score_rows_subset], axis=1)

        # 將所有數值欄位轉為數字
        for col in df.columns:
            if col not in ['單位', '姓名', '性別', '備註']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 建立年齡層
        if '年齡' in df.columns:
            bins = [20, 30, 40, 50, 70]
            labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
            df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        
        # 定義清單供介面使用
        score_metrics = [c for c in score_rows_subset.columns if '備註' not in c and '名次' not in c]
        record_metrics = [c for c in df.columns if '_紀錄' in c]

        return df, score_metrics, record_metrics
    except Exception as e:
        st.error(f"資料處理失敗。錯誤訊息：{e}")
        return None, [], []

df, score_metrics, record_metrics = load_and_clean_data()

# --- 2. 介面呈現 ---
if df is not None:
    # 頂部 KPI
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("受測總人數", f"{len(df)} 人")
    with k2: st.metric("測驗項目數", f"{len(score_metrics) - 3} 項") # 扣除合計項
    with k3: st.metric("單位總數", f"{df['單位'].nunique()}")
    with k4: 
        if '總成績' in df.columns:
            st.metric("全大隊平均分", f"{df['總成績'].mean():.1f}")

    tab_overview, tab_individual, tab_ranking = st.tabs([
        "📊 大隊分析", "🎯 個人分析", "🏆 成績排行"
    ])

    with tab_overview:
        selected_m = st.selectbox("選擇要查看的項目：", score_metrics, index=len(score_metrics)-1)
        c1, c2 = st.columns(2)
        with c1:
            avg_df = df.groupby('單位')[selected_m].mean().reset_index().sort_values(by=selected_m, ascending=False)
            fig_bar = px.bar(avg_df, x='單位', y=selected_m, color='單位', text_auto='.1f', title=f"各單位 {selected_m} 平均分數")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_box = px.box(df, x='單位', y=selected_m, color='性別', points="all", hover_data=['姓名'], title=f"{selected_m} 分數分佈情形")
            st.plotly_chart(fig_box, use_container_width=True)

    with tab_individual:
        p_name = st.selectbox("搜尋隊員姓名", df['姓名'].unique())
        person = df[df['姓名'] == p_name].iloc[0]
        
        col_info, col_graph = st.columns([1, 2])
        with col_info:
            st.success(f"### {person['姓名']}")
            st.write(f"**單位：** {person['單位']}")
            st.write(f"**總成績：** {person['總成績']}")
            st.write("---")
            st.write("**詳細測驗紀錄：**")
            # 整理成表格顯示
            display_rec = []
            for m in score_metrics:
                if '合計' not in m and '成績' not in m:
                    rec_val = person.get(f"{m}_紀錄", "N/A")
                    score_val = person.get(m, "N/A")
                    display_rec.append({"項目": m, "原始紀錄": rec_val, "得分": score_val})
            st.table(pd.DataFrame(display_rec))

        with col_graph:
            # 雷達圖（排除合計與總分）
            radar_items = [m for m in score_metrics if '合計' not in m and '總成績' not in m]
            radar_df = pd.DataFrame({
                "項目": radar_items,
                "分數": [person[m] for m in radar_items]
            })
            fig_radar = px.line_polar(radar_df, r='分數', theta='項目', line_close=True, range_r=[0, 100])
            fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
            st.plotly_chart(fig_radar, use_container_width=True)

    with tab_ranking:
        st.subheader("🏆 全大隊成績總表")
        # 選擇重要欄位顯示
        cols_to_show = ['單位', '姓名', '年齡', '體能合計40%', '技能合計60%', '總成績']
        available_cols = [c for c in cols_to_show if c in df.columns]
        rank_df = df[available_cols].sort_values(by='總成績', ascending=False)
        st.dataframe(rank_df, use_container_width=True, hide_index=True)

else:
    st.info("正在讀取資料，請稍候...")
