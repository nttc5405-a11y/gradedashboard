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

st.title("🚒 成功消防大隊 - 體技能戰情室 3.0 (請假自動過濾版)")

@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        raw_df = pd.read_csv(url)
        
        # 1. 向下填補：解決合併儲存格導致分數列沒有名字與單位的情況
        # 這次也把「備註」放進填補清單，確保請假資訊不遺失
        id_cols = ['NO.', '單位', '姓名', '性別', '年齡', '備註']
        raw_df[id_cols] = raw_df[id_cols].ffill()

        # 2. 移除完全空白的行 (以 NO. 為準)
        raw_df = raw_df.dropna(subset=['NO.']).reset_index(drop=True)

        # 3. 確保資料為偶數（紀錄+分數）
        if len(raw_df) % 2 != 0:
            raw_df = raw_df.iloc[:-1]

        # 4. 分離紀錄與分數
        records = raw_df.iloc[::2].reset_index(drop=True)
        scores = raw_df.iloc[1::2].reset_index(drop=True)

        # 5. 定義測驗項目欄位
        exclude_cols = ['NO.', '單位', '姓名', '性別', '年齡', '備註', '名次']
        test_items = [c for c in records.columns if c not in exclude_cols]

        # 6. 處理紀錄列 (改名加後綴)
        records_renamed = records[id_cols].copy()
        for col in test_items:
            records_renamed[f"{col}_紀錄"] = records[col]

        # 7. 處理分數列 (只取數值，避開重複 ID 防止錯誤)
        score_data = scores[test_items].copy()
        
        # 8. 橫向合併 (31或62位隊員，一人一行)
        df = pd.concat([records_renamed, score_data], axis=1)

        # 9. 將數值欄位轉為數字，文字(如請假)會變 NaN (不影響計算平均)
        numeric_cols = [c for c in df.columns if c not in ['單位', '姓名', '性別', '備註', '年齡層']]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 10. 建立年齡層
        if '年齡' in df.columns:
            bins = [20, 30, 40, 50, 70]
            labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
            df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)

        return df, test_items
    except Exception as e:
        st.error(f"資料處理失敗：{e}")
        return None, []

df, score_metrics = load_and_clean_data()

if df is not None:
    # --- KPI 區：處理請假統計 ---
    # 總人數 (含請假)
    total_people = len(df)
    # 實際測驗人數 (總成績欄位不是 NaN 的人)
    tested_people = df['總成績'].dropna().count()
    leave_people = total_people - tested_people

    k1, k2, k3, k4 = st.columns(4)
    with k1: 
        st.metric("名冊總人數", f"{total_people} 人")
        st.caption(f"實際受測：{tested_people} | 請假：{leave_people}")
    with k2: 
        max_s = df['總成績'].max()
        st.metric("大隊最高分", f"{max_s:.1f}" if pd.notna(max_s) else "0")
    with k3: st.metric("受測單位數", f"{df['單位'].nunique()}")
    with k4: 
        avg_s = df['總成績'].mean()
        st.metric("全大隊平均 (排除請假)", f"{avg_s:.1f}" if pd.notna(avg_s) else "0")

    tab1, tab2, tab3 = st.tabs(["📊 數據分析", "🎯 個人分析", "🏆 成績排行"])

    # --- Tab 1: 大隊總覽 (自動排除請假人員) ---
    with tab1:
        selected_m = st.selectbox("選擇指標：", score_metrics, index=len(score_metrics)-1)
        c1, c2 = st.columns(2)
        with c1:
            # groupby 會自動排除 NaN (請假者)，不會拉低平均
            avg_df = df.groupby('單位')[selected_m].mean().reset_index().sort_values(by=selected_m, ascending=False)
            fig_bar = px.bar(avg_df, x='單位', y=selected_m, color='單位', text_auto='.1f', title=f"各分隊 {selected_m} 平均 (不計請假)")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            # 盒鬚圖也會自動排除請假者
            fig_box = px.box(df, x='單位', y=selected_m, color='性別', points="all", hover_data=['姓名'], title=f"{selected_m} 成績分佈")
            st.plotly_chart(fig_box, use_container_width=True)

    # --- Tab 2: 個人分析 (處理請假顯示) ---
    with tab2:
        p_name = st.selectbox("搜尋隊員姓名", df['姓名'].unique())
        person = df[df['姓名'] == p_name].iloc[0]
        
        ci, cg = st.columns([1, 2])
        with ci:
            st.success(f"### {person['姓名']}")
            st.write(f"**單位：** {person['單位']} | **備註：** {person['備註']}")
            
            # 如果是請假人員，顯示警告提示
            if pd.isna(person['總成績']):
                st.warning(f"⚠️ 偵測到此人員當次測驗：{person['備註']}")
            else:
                st.write(f"**總成績：** {person['總成績']}")
            
            # 詳細數據表格
            details = []
            for item in score_metrics:
                if '合計' not in item and '總成績' not in item:
                    details.append({
                        "項目": item,
                        "原始紀錄": person.get(f"{item}_紀錄", "N/A"),
                        "得分": person.get(item, 0)
                    })
            st.table(pd.DataFrame(details))

        with cg:
            # 如果是請假，雷達圖會是空的
            if pd.isna(person['總成績']):
                st.info("請假人員無雷達圖數據")
            else:
                radar_items = [m for m in score_metrics if '合計' not in m and '總成績' not in m]
                radar_df = pd.DataFrame({"項目": radar_items, "分數": [person[m] for m in radar_items]})
                fig_radar = px.line_polar(radar_df, r='分數', theta='項目', line_close=True, range_r=[0, 100])
                fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
                st.plotly_chart(fig_radar, use_container_width=True)

    # --- Tab 3: 排行榜 ---
    with tab3:
        st.subheader("🏆 全大隊成績總表")
        rank_cols = ['單位', '姓名', '年齡', '備註', '體能合計40%', '技能合計60%', '總成績']
        display_df = df[[c for c in rank_cols if c in df.columns]].sort_values(by='總成績', ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.info("正在連線至資料庫...")
