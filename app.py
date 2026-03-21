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

st.title("🚒 成功消防大隊 - 體技能戰情室 3.0 (自動合併版)")

# --- 1. 資料讀取與清洗邏輯 (處理兩列合併) ---
@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        raw_df = pd.csv(url)
        
        # 1. 基本清理：移除全空行
        raw_df = raw_df.dropna(subset=['單位'], how='all').reset_index(drop=True)

        # 2. 分離「紀錄列」與「分數列」
        data_rows = raw_df.iloc[::2].reset_index(drop=True)
        score_rows = raw_df.iloc[1::2].reset_index(drop=True)

        # 3. 定義基本資料欄位
        base_info_cols = ['NO.', '單位', '姓名', '性別', '年齡']
        
        # 4. 處理「紀錄列」：除了基本資料外，其餘項目加上 "_紀錄"
        # 這樣就不會跟後面的分數欄位撞名了
        data_cols_renamed = {}
        for col in data_rows.columns:
            if col not in base_info_cols and '備註' not in col and '名次' not in col:
                data_cols_renamed[col] = f"{col}_紀錄"
        data_rows = data_rows.rename(columns=data_cols_renamed)

        # 5. 處理「分數列」：只保留分數的部分
        # 我們要把分數列中的 '體能合計', '總成績' 等欄位保留下來作為主要數據
        other_cols = [c for c in score_rows.columns if c not in base_info_cols]
        score_rows_subset = score_rows[other_cols]

        # 6. 橫向合併 (這時候欄位名稱已經完全唯一了)
        df = pd.concat([data_rows, score_rows_subset], axis=1)

        # 7. 將所有非文字欄位轉為數字
        # 我們排除掉基本資料欄位，剩下的通通轉數字
        for col in df.columns:
            if col not in ['單位', '姓名', '性別', '備註']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 8. 建立年齡層
        if '年齡' in df.columns:
            bins = [20, 30, 40, 50, 70]
            labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
            df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        
        # 9. 重新定義圖表要用的分數清單
        # 只要不是基本資料、不是「_紀錄」結尾、不是備註，就是分數
        score_metrics = [c for c in score_rows_subset.columns if '備註' not in c and '名次' not in c]
        # 紀錄清單（用於個人明細）
        record_metrics = [c for c in df.columns if '_紀錄' in c]

        return df, score_metrics, record_metrics
    except Exception as e:
        st.error(f"資料處理失敗。錯誤訊息：{e}")
        # 這裡多加一個 debug 資訊，幫你看看目前抓到的欄位
        if 'df' in locals():
            st.write("目前偵測到的欄位有：", df.columns.tolist())
        return None, [], []

df, score_metrics, record_metrics = load_and_clean_data()

# --- 2. 介面呈現 ---
if df is not None:
    # 頂部儀表板資訊
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("受測總人數", f"{len(df)} 人")
    with k2: st.metric("測驗項目數", f"{len(record_metrics)} 項")
    with k3: st.metric("受測單位數", f"{df['單位'].nunique()} 個")
    with k4: 
        avg_total = df['總成績'].mean()
        st.metric("大隊平均分", f"{avg_total:.1f}")

    tab_overview, tab_individual, tab_ranking = st.tabs([
        "📊 大隊總覽", "🎯 個人分析", "🏆 成績排行"
    ])

    # --- Tab 1: 大隊分析 ---
    with tab_overview:
        selected_m = st.selectbox("選擇分析項目（分數）：", score_metrics, index=len(score_metrics)-1)
        
        c1, c2 = st.columns(2)
        with c1:
            avg_df = df.groupby('單位')[selected_m].mean().reset_index().sort_values(by=selected_m, ascending=False)
            fig_bar = px.bar(avg_df, x='單位', y=selected_m, color='單位', text_auto='.1f', title=f"各單位 {selected_m} 平均表現")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_box = px.box(df, x='單位', y=selected_m, color='性別', points="all", hover_data=['姓名'], title=f"{selected_m} 分數分佈")
            st.plotly_chart(fig_box, use_container_width=True)

    # --- Tab 2: 個人雷達圖與明細 ---
    with tab_individual:
        col_sel, col_graph = st.columns([1, 2])
        with col_sel:
            p_name = st.selectbox("搜尋隊員姓名", df['姓名'].unique())
            person = df[df['姓名'] == p_name].iloc[0]
            st.info(f"**姓名：** {person['姓名']}  \n**單位：** {person['單位']}  \n**總成績：** {person['總成績']}")
            
            # 顯示原始紀錄小表格
            st.write("**原始測驗紀錄：**")
            rec_df = pd.DataFrame({
                "項目": record_metrics,
                "紀錄": [person[m] for m in record_metrics]
            })
            st.dataframe(rec_df, hide_index=True)

        with col_graph:
            # 製作雷達圖（僅選取單項分數，不含合計項）
            radar_items = [m for m in score_metrics if '_分數' in m]
            radar_df = pd.DataFrame({
                "項目": [m.replace('_分數', '') for m in radar_items],
                "分數": [person[m] for m in radar_items]
            })
            fig_radar = px.line_polar(radar_df, r='分數', theta='項目', line_close=True, range_r=[0, 100])
            fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
            fig_radar.update_layout(title=f"{p_name} 體技能分佈圖")
            st.plotly_chart(fig_radar, use_container_width=True)

    # --- Tab 3: 排行榜 ---
    with tab_ranking:
        st.subheader("🏆 全大隊成績總表")
        display_df = df[['單位', '姓名', '年齡', '體能合計40%', '技能合計60%', '總成績']].sort_values(by='總成績', ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.warning("請確認 Google Sheet 已發佈為 CSV，且網址已正確放入 Secrets 中。")
