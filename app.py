import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="成功消防大隊 - 戰情室 3.0", page_icon="🚒", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 18px; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能戰情室 3.0 (動態擴展版)")

# --- 定義系統基本欄位 (不會被當成測驗項目的欄位) ---
BASE_COLS = ['測驗日期', '分隊', '姓名', '性別', '年齡', '年齡層']

@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        df = pd.read_csv(url)
        
        # 魔法 1：自動抓出所有的「測驗項目」
        # 只要不在 BASE_COLS 裡面的欄位，通通視為測驗項目
        dynamic_metrics = [col for col in df.columns if col not in ['測驗日期', '分隊', '姓名', '性別', '年齡']]
        
        # 將抓到的測驗項目通通轉為數字
        for m in dynamic_metrics:
            df[m] = pd.to_numeric(df[m], errors='coerce')
        
        bins = [20, 30, 40, 50, 70]
        labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
        df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        df = df.sort_values(by=['姓名', '測驗日期'])
        
        return df, dynamic_metrics
    except Exception as e:
        st.error(f"資料讀取失敗，請檢查。錯誤訊息：{e}")
        return None, []

df, test_metrics = load_and_clean_data()

if df is not None and len(test_metrics) > 0:
    all_dates = sorted(df['測驗日期'].unique(), reverse=True)
    latest_date = all_dates[0]
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("本次測驗總人數", f"{len(df[df['測驗日期']==latest_date])} 人")
    with k2: st.metric("動態追蹤項目數", f"{len(test_metrics)} 項")
    with k3: st.metric("受測分隊數", f"{df['分隊'].nunique()} 個")
    with k4: st.metric("最新測驗日期", f"{latest_date}")

    tab_overview, tab_group, tab_individual, tab_alert = st.tabs([
        "📊 戰情總覽", "🔍 交叉分析", "🎯 個人雷達", "🚨 自訂警示"
    ])

    # --- Tab 1: 大隊戰情總覽 ---
    with tab_overview:
        # 魔法 2：下拉選單吃動態清單 test_metrics
        selected_metric = st.selectbox("請選擇觀測項目：", test_metrics, key='ov_m')
        
        c1, c2 = st.columns(2)
        with c1:
            # 修正：只抓取「最新一次測驗」的資料來算各分隊平均
            latest_df = df[df['測驗日期'] == latest_date]
            avg_df = latest_df.groupby('分隊')[selected_metric].mean().reset_index()
            
            # 標題加上最新日期，讓長官一目了然
            fig_bar = px.bar(avg_df, x='分隊', y=selected_metric, color='分隊', text_auto='.1f', title=f"各分隊 {selected_metric} 現況戰力 ({latest_date})")
            
            if '秒' in selected_metric: fig_bar.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            trend_df = df.groupby('測驗日期')[selected_metric].mean().reset_index()
            fig_line = px.line(trend_df, x='測驗日期', y=selected_metric, markers=True, title=f"大隊 {selected_metric} 趨勢")
            if '秒' in selected_metric: fig_line.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_line, use_container_width=True)

    # --- Tab 2: 族群交叉分析 ---
    with tab_group:
        f1, f2, f3, f4 = st.columns(4)
        with f1: s_gen = st.multiselect("性別", df['性別'].unique(), default=df['性別'].unique().tolist())
        with f2: s_age = st.multiselect("年齡層", df['年齡層'].dropna().unique().tolist(), default=df['年齡層'].dropna().unique().tolist())
        with f3: s_team = st.multiselect("分隊", df['分隊'].unique(), default=df['分隊'].unique().tolist())
        with f4: s_met = st.selectbox("分析項目", test_metrics, key='gr_m')
        
        filtered = df[(df['性別'].isin(s_gen)) & (df['年齡層'].isin(s_age)) & (df['分隊'].isin(s_team))]
        if not filtered.empty:
            fig_box = px.box(filtered, x="分隊", y=s_met, color="性別", points="all", hover_data=['姓名'])
            if '秒' in s_met: fig_box.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.warning("⚠️ 找不到符合條件的資料。")

    # --- Tab 3: 個人追蹤儀表 (導入 PR 值雷達圖) ---
    with tab_individual:
        cp1, cp2 = st.columns([1, 2])
        with cp1:
            p_name = st.selectbox("選擇隊員", df['姓名'].unique())
            person_all_data = df[df['姓名'] == p_name].sort_values(by='測驗日期', ascending=False)
            p_latest = person_all_data.iloc[0]
            st.info(f"**姓名：** {p_latest['姓名']} | **單位：** {p_latest['分隊']}")
            
            st.write("**最新成績明細：**")
            for m in test_metrics:
                st.write(f"- {m}：{p_latest[m]}")
                
        with cp2:
            # 魔法 3：動態計算所有項目的 PR 值 (打敗大隊多少人)
            radar_scores = []
            valid_metrics = []
            
            for m in test_metrics:
                val = p_latest[m]
                if pd.notna(val):
                    # 抓取最新一次測驗的全大隊成績當作母體
                    latest_all = df[df['測驗日期'] == latest_date][m].dropna()
                    if len(latest_all) > 0:
                        # 秒數越低越好，其他越高越好
                        if '秒' in m:
                            pr = (latest_all > val).mean() * 100
                        else:
                            pr = (latest_all < val).mean() * 100
                        radar_scores.append(pr)
                        valid_metrics.append(m)

            if len(valid_metrics) > 2:
                radar_df = pd.DataFrame({'項目': valid_metrics, 'PR值 (大隊百分等級)': radar_scores})
                fig_radar = px.line_polar(radar_df, r='PR值 (大隊百分等級)', theta='項目', line_close=True, range_r=[0, 100])
                fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
                st.plotly_chart(fig_radar, use_container_width=True)
                st.markdown("<span style='font-size:12px; color:gray;'>*註：雷達圖顯示為 PR 值，100 分代表該項目成績為全大隊第一名。*</span>", unsafe_allow_html=True)
            else:
                st.warning("該員有效成績項目不足，無法繪製雷達圖。")

    # --- Tab 4: 自訂警示區 (動態化) ---
    with tab_alert:
        ca1, ca2 = st.columns(2)
        with ca1:
            st.markdown("##### 🔥 自訂退步監控")
            reg_m = st.selectbox("監控退步項目：", test_metrics, key='al_r1')
            reg_val = st.number_input("容許退步空間 (數值)：", value=30 if '秒' in reg_m else 5)
            
            if len(all_dates) > 1:
                d_now = df[df['測驗日期']==all_dates[0]][['姓名', '分隊', reg_m]]
                d_old = df[df['測驗日期']==all_dates[1]][['姓名', reg_m]]
                merged = pd.merge(d_now, d_old, on='姓名', suffixes=('_今', '_昨')).dropna()
                
                # 自動判斷退步邏輯
                if '秒' in reg_m:
                    merged['退步幅度'] = merged[f'{reg_m}_今'] - merged[f'{reg_m}_昨']
                else:
                    merged['退步幅度'] = merged[f'{reg_m}_昨'] - merged[f'{reg_m}_今']
                    
                regression = merged[merged['退步幅度'] > reg_val].sort_values(by='退步幅度', ascending=False)
                
                if not regression.empty:
                    st.dataframe(regression[['姓名', '分隊', '退步幅度']], hide_index=True, use_container_width=True)
                else:
                    st.success("🎉 無人觸發退步警示！")
            else:
                st.info("資料不足兩次，無法比對。")

        with ca2:
            st.markdown("##### ❌ 自訂未達標監控")
            fail_m = st.selectbox("監控達標項目：", test_metrics, key='al_f1')
            fail_val = st.number_input("最低標準 (秒數請填上限，次數請填下限)：", value=870 if '秒' in fail_m else 6)
            
            # 自動判斷不及格邏輯
            if '秒' in fail_m:
                fail_list = df[(df['測驗日期']==latest_date) & (df['姓名'].notna()) & (df[fail_m] > fail_val)]
            else:
                fail_list = df[(df['測驗日期']==latest_date) & (df['姓名'].notna()) & (df[fail_m] < fail_val)]
                
            if not fail_list.empty:
                st.dataframe(fail_list[['姓名', '分隊', fail_m]], hide_index=True, use_container_width=True)
            else:
                st.success("🎉 全員通過此項目標準！")
else:
    st.info("等待讀取資料庫...")
