import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 頁面設定 ---
st.set_page_config(page_title="成功消防大隊 - 戰情室 3.0", page_icon="🚒", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能戰情室 3.0 (62列/31人合併版)")

@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        # 讀取資料
        raw_df = pd.read_csv(url)
        
        # 1. 基礎清理：移除全空行，並確保「姓名」欄位存在
        raw_df = raw_df.dropna(subset=['姓名'], how='all').reset_index(drop=True)

        # 2. 依照你的邏輯分離：
        # 偶數列 (0, 2, 4...) -> 原始紀錄 (1-based 是 2, 4, 6, 8...)
        # 奇數列 (1, 3, 5...) -> 換算分數 (1-based 是 3, 5, 7, 9...)
        records = raw_df.iloc[::2].reset_index(drop=True)
        scores = raw_df.iloc[1::2].reset_index(drop=True)

        # 3. 定義身分欄位
        id_cols = ['NO.', '單位', '姓名', '性別', '年齡']
        
        # 4. 處理「紀錄列」：所有測驗項目的欄位名加上 "_紀錄"
        test_items = [c for c in records.columns if c not in id_cols and '備註' not in c and '名次' not in c]
        records_renamed = records[id_cols].copy()
        for col in test_items:
            records_renamed[f"{col}_紀錄"] = records[col]

        # 5. 處理「分數列」：只保留分數數值，並丟棄重複的身分資訊
        # 這樣就不會出現兩個「姓名」欄位導致 DuplicateError
        score_data = scores[test_items].copy()
        
        # 6. 合併：將 31 位隊員的「身分+紀錄」與「分數」橫向拼接
        df = pd.concat([records_renamed, score_data], axis=1)

        # 7. 數值化處理
        numeric_cols = [c for c in df.columns if c not in ['單位', '姓名', '性別', '備註']]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 建立年齡層
        if '年齡' in df.columns:
            bins = [20, 30, 40, 50, 70]
            labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
            df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)

        # 提取分數清單用於選單 (包含合計、總成績、及單項分數)
        score_metrics = test_items
        
        return df, score_metrics, test_items
    except Exception as e:
        st.error(f"資料處理失敗：{e}")
        return None, [], []

df, score_metrics, original_test_names = load_and_clean_data()

if df is not None:
    # --- KPI 區 ---
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("受測隊員數", f"{len(df)} 位")
    with k2: st.metric("最高總分", f"{df['總成績'].max():.1f}")
    with k3: st.metric("受測單位數", f"{df['單位'].nunique()}")
    with k4: st.metric("大隊平均總分", f"{df['總成績'].mean():.1f}")

    tab1, tab2, tab3 = st.tabs(["📊 數據分析", "🎯 個人戰力", "🏆 成績排行"])

    # --- Tab 1: 大隊總覽 ---
    with tab1:
        selected_m = st.selectbox("請選擇分析指標（分數）：", score_metrics, index=len(score_metrics)-1)
        c1, c2 = st.columns(2)
        with c1:
            avg_df = df.groupby('單位')[selected_m].mean().reset_index().sort_values(by=selected_m, ascending=False)
            fig_bar = px.bar(avg_df, x='單位', y=selected_m, color='單位', text_auto='.1f', title=f"各單位 {selected_m} 平均分數")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_box = px.box(df, x='單位', y=selected_m, color='性別', points="all", hover_data=['姓名'], title=f"{selected_m} 分數分佈")
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
            
            # 製作詳細細節表 (紀錄 vs 分數)
            details = []
            for item in original_test_names:
                if '合計' not in item and '總成績' not in item:
                    details.append({
                        "測驗項目": item,
                        "原始紀錄": person.get(f"{item}_紀錄", "N/A"),
                        "得分": person.get(item, 0)
                    })
            st.table(pd.DataFrame(details))

        with cg:
            # 雷達圖 (排除總分與合計項)
            radar_items = [m for m in score_metrics if '合計' not in m and '總成績' not in m]
            radar_df = pd.DataFrame({"項目": radar_items, "分數": [person[m] for m in radar_items]})
            fig_radar = px.line_polar(radar_df, r='分數', theta='項目', line_close=True, range_r=[0, 100])
            fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
            st.plotly_chart(fig_radar, use_container_width=True)

    # --- Tab 3: 排行榜 ---
    with tab3:
        st.subheader("🏆 全大隊成績排行")
        rank_cols = ['單位', '姓名', '年齡', '體能合計40%', '技能合計60%', '總成績']
        display_df = df[[c for c in rank_cols if c in df.columns]].sort_values(by='總成績', ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.info("請檢查 Secrets 中的 URL 以及試算表權限。")
