import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 頁面基本設定 ---
st.set_page_config(page_title="成功消防大隊 - 戰情室 3.0", page_icon="🚒", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能戰情室 3.0 (穩定版)")

@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        raw_df = pd.read_csv(url)
        
        # 1. 移除全空行與標題重複行
        raw_df = raw_df.dropna(subset=['姓名']).reset_index(drop=True)

        # 2. 分離：偶數列是「紀錄」，奇數列是「分數」
        # 每位隊員佔 2 列，所以 62 列資料會產生 31 位隊員
        data_rows = raw_df.iloc[::2].reset_index(drop=True)
        score_rows = raw_df.iloc[1::2].reset_index(drop=True)

        # 定義身分欄位
        id_cols = ['NO.', '單位', '姓名', '性別', '年齡']
        
        # 3. 處理紀錄列 (加上 _紀錄 後綴)
        # 找出除了身分欄位以外的測驗項目
        test_items = [c for c in data_rows.columns if c not in id_cols and '備註' not in c]
        
        data_rows_renamed = data_rows[id_cols].copy()
        for item in test_items:
            data_rows_renamed[f"{item}_紀錄"] = data_rows[item]

        # 4. 處理分數列 (加上 _分數 後綴)
        # 我們只需要分數數值，不需要重複的姓名單位
        score_rows_renamed = pd.DataFrame()
        for item in test_items:
            # 針對總成績或合計，維持原本名稱方便顯示，其他的加上 _分數
            if '合計' in item or '總成績' in item:
                score_rows_renamed[item] = score_rows[item]
            else:
                score_rows_renamed[f"{item}_分數"] = score_rows[item]

        # 5. 強制橫向合併 (31位隊員，每一位現在都有一長串唯一的欄位)
        df = pd.concat([data_rows_renamed, score_rows_renamed], axis=1)

        # 6. 轉數字處理
        cols_to_fix = [c for c in df.columns if c not in ['單位', '姓名', '性別']]
        for col in cols_to_fix:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 建立年齡層
        if '年齡' in df.columns:
            bins = [20, 30, 40, 50, 70]
            labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
            df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)

        # 定義繪圖用的清單
        # 分數清單：包含「_分數」結尾以及「總成績/合計」
        all_score_metrics = [c for c in score_rows_renamed.columns if '備註' not in c]
        
        return df, all_score_metrics, test_items
    except Exception as e:
        st.error(f"資料處理失敗：{e}")
        return None, [], []

df, score_metrics, original_tests = load_and_clean_data()

if df is not None:
    # --- KPI 區 ---
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("受測總人數", f"{len(df)} 人")
    with k2: st.metric("最高總分數", f"{df['總成績'].max() if '總成績' in df.columns else 0:.1f}")
    with k3: st.metric("受測分隊數", f"{df['單位'].nunique()}")
    with k4: st.metric("平均總分", f"{df['總成績'].mean() if '總成績' in df.columns else 0:.1f}")

    tab1, tab2, tab3 = st.tabs(["📊 大隊總覽", "🎯 個人分析", "🏆 排行榜"])

    # --- Tab 1: 大隊分析 ---
    with tab1:
        selected_m = st.selectbox("請選擇分析指標：", score_metrics, index=len(score_metrics)-1)
        c1, c2 = st.columns(2)
        with c1:
            avg_df = df.groupby('單位')[selected_m].mean().reset_index().sort_values(by=selected_m, ascending=False)
            fig_bar = px.bar(avg_df, x='單位', y=selected_m, color='單位', text_auto='.1f', title=f"各分隊 {selected_m} 平均")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            # 這裡解決了 DuplicateError，因為欄位名現在是唯一的
            fig_box = px.box(df, x='單位', y=selected_m, color='性別', points="all", hover_data=['姓名'], title=f"{selected_m} 分佈情況")
            st.plotly_chart(fig_box, use_container_width=True)

    # --- Tab 2: 個人分析 ---
    with tab2:
        p_name = st.selectbox("搜尋隊員姓名", df['姓名'].unique())
        person = df[df['姓名'] == p_name].iloc[0]
        
        ci, cg = st.columns([1, 2])
        with ci:
            st.success(f"### {person['姓名']}")
            st.write(f"**單位：** {person['單位']} | **年齡：** {person['年齡']}")
            st.write(f"**總成績：** {person['總成績']}")
            
            # 顯示數據表格
            details = []
            for item in original_tests:
                if '合計' not in item and '總成績' not in item:
                    details.append({
                        "測驗項目": item,
                        "原始紀錄": person.get(f"{item}_紀錄", "N/A"),
                        "得分": person.get(f"{item}_分數", 0)
                    })
            st.table(pd.DataFrame(details))

        with cg:
            # 雷達圖邏輯
            radar_items = [m for m in score_metrics if '合計' not in m and '總成績' not in m]
            radar_df = pd.DataFrame({
                "項目": [m.replace('_分數', '') for m in radar_items],
                "分數": [person[m] for m in radar_items]
            })
            fig_radar = px.line_polar(radar_df, r='分數', theta='項目', line_close=True, range_r=[0, 100])
            fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
            st.plotly_chart(fig_radar, use_container_width=True)

    # --- Tab 3: 排行榜 ---
    with tab3:
        st.subheader("🏆 全大隊成績排行")
        # 只顯示關鍵欄位
        rank_cols = ['單位', '姓名', '年齡', '體能合計40%', '技能合計60%', '總成績']
        display_df = df[[c for c in rank_cols if c in df.columns]].sort_values(by='總成績', ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.info("請檢查 Google Sheet 權限與 Secret URL 設定。")
