import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 頁面基本設定 ---
st.set_page_config(page_title="成功消防大隊 - 戰情室 3.0", page_icon="🚒", layout="wide")

# 自訂 CSS
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 18px; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能戰情室 3.0 (穩定運作版)")

# --- 1. 資料讀取與清洗 (解決命名衝突) ---
@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        raw_df = pd.read_csv(url)
        
        # 移除全空行
        raw_df = raw_df.dropna(subset=['單位'], how='all').reset_index(drop=True)

        # 分離：第一列是紀錄，第二列是分數
        data_rows = raw_df.iloc[::2].reset_index(drop=True)
        score_rows = raw_df.iloc[1::2].reset_index(drop=True)

        # 定義基本資料欄位
        base_cols = ['NO.', '單位', '姓名', '性別', '年齡']
        
        # 【重要步驟】重命名紀錄列的所有欄位，加上後綴 "_紀錄"
        # 這樣就不會跟分數列的「總成績」、「體能合計」撞名了
        new_data_cols = {}
        for col in data_rows.columns:
            if col not in base_cols and '備註' not in col:
                new_data_cols[col] = f"{col}_紀錄"
        data_rows = data_rows.rename(columns=new_data_cols)

        # 處理分數列：只保留我們要的分數數值
        # 排除掉基本資料欄位，避免合併後出現 姓名_x, 姓名_y
        score_only_cols = [c for c in score_rows.columns if c not in base_cols]
        score_rows_subset = score_rows[score_only_cols]

        # 橫向合併 (紀錄 + 分數)
        df = pd.concat([data_rows, score_rows_subset], axis=1)

        # 排除非數值欄位，其餘通通轉數字
        # 這裡會逐一欄位轉換，避免 ambiguous 錯誤
        for col in df.columns:
            if col not in ['單位', '姓名', '性別', '備註', '名次', '年齡層']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 建立年齡層
        if '年齡' in df.columns:
            bins = [20, 30, 40, 50, 70]
            labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
            df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        
        # 定義清單供後續使用
        score_metrics = [c for c in score_only_cols if '備註' not in c and '名次' not in c]
        
        return df, score_metrics
    except Exception as e:
        st.error(f"資料處理失敗。錯誤訊息：{e}")
        return None, []

df, score_metrics = load_and_clean_data()

# --- 2. 介面呈現 ---
if df is not None:
    # 頂部 KPI 區
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("受測總人數", f"{len(df)} 人")
    with k2: 
        max_score = df['總成績'].max()
        st.metric("大隊最高分", f"{max_score:.1f}")
    with k3: st.metric("單位總數", f"{df['單位'].nunique()}")
    with k4: 
        avg_score = df['總成績'].mean()
        st.metric("大隊平均分", f"{avg_score:.1f}")

    tab_overview, tab_individual, tab_ranking = st.tabs(["📊 大隊趨勢", "🎯 個人分析", "🏆 成績排行"])

    # 大隊分析
    with tab_overview:
        selected_m = st.selectbox("選擇分析指標（分數）：", score_metrics, index=len(score_metrics)-1)
        c1, c2 = st.columns(2)
        with c1:
            avg_df = df.groupby('單位')[selected_m].mean().reset_index().sort_values(by=selected_m, ascending=False)
            fig_bar = px.bar(avg_df, x='單位', y=selected_m, color='單位', text_auto='.1f', title=f"各單位 {selected_m} 平均表現")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_box = px.box(df, x='單位', y=selected_m, color='性別', points="all", hover_data=['姓名'], title=f"{selected_m} 分數分佈")
            st.plotly_chart(fig_box, use_container_width=True)

    # 個人分析
    with tab_individual:
        p_name = st.selectbox("搜尋隊員姓名", df['姓名'].unique())
        person = df[df['姓名'] == p_name].iloc[0]
        
        ci, cg = st.columns([1, 2])
        with ci:
            st.success(f"### {person['姓名']}")
            st.write(f"**所屬單位：** {person['單位']}")
            st.write(f"**總成績：** {person['總成績']}")
            st.write("---")
            # 建立細節表格
            details = []
            for m in score_metrics:
                if '合計' not in m and '成績' not in m:
                    details.append({
                        "項目": m,
                        "原始紀錄": person.get(f"{m}_紀錄", "N/A"),
                        "得分": person.get(m, 0)
                    })
            st.table(pd.DataFrame(details))

        with cg:
            # 雷達圖
            radar_items = [m for m in score_metrics if '合計' not in m and '成績' not in m]
            radar_df = pd.DataFrame({"項目": radar_items, "分數": [person[m] for m in radar_items]})
            fig_radar = px.line_polar(radar_df, r='分數', theta='項目', line_close=True, range_r=[0, 100])
            fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
            st.plotly_chart(fig_radar, use_container_width=True)

    # 排行榜
    with tab_ranking:
        st.subheader("🏆 全大隊成績排行")
        rank_cols = ['單位', '姓名', '年齡', '體能合計40%', '技能合計60%', '總成績']
        available = [c for c in rank_cols if c in df.columns]
        st.dataframe(df[available].sort_values(by='總成績', ascending=False), use_container_width=True, hide_index=True)

else:
    st.warning("等待資料載入中，請檢查連結與 Secrets 設定。")
