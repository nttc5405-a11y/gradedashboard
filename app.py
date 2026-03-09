import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="成功消防大隊 - 戰情室 2.0", page_icon="🚒", layout="wide")

# 套用一點簡單的 CSS 讓指標卡更漂亮
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能科學化訓練戰情室 2.0")

# --- 2. 串接與資料預處理 (Data Cleaning) ---
@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        # 這裡沿用您設定在 Secrets 裡的網址
        url = st.secrets["sheet_url"]
        df = pd.read_csv(url)
        
        # [優化] 強制將成績欄位轉為數字，非數字(如公假)會變成空值 NaN，避免運算錯誤
        metrics = ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數']
        for m in metrics:
            df[m] = pd.to_numeric(df[m], errors='coerce')
        
        # [優化] 年齡分層
        bins = [20, 30, 40, 50, 65]
        labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
        df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        
        # 排序日期
        df = df.sort_values(by=['姓名', '測驗日期'])
        return df
    except Exception as e:
        st.error(f"資料讀取錯誤：{e}")
        return None

df = load_and_clean_data()

if df is not None:
    # --- 3. 戰情指標區 (KPI Metrics) ---
    # 抓取最新與次新測驗日期來計算進步幅度
    all_dates = sorted(df['測驗日期'].unique(), reverse=True)
    latest_date = all_dates[0]
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    with col_kpi1:
        st.metric("本次測驗總人數", f"{len(df[df['測驗日期']==latest_date])} 人")
    
    with col_kpi2:
        # 假設 3000m 及格標準為 870秒 (14:30)
        pass_run = df[(df['測驗日期']==latest_date) & (df['3000公尺跑步_秒'] <= 870)]
        pass_rate = (len(pass_run) / len(df[df['測驗日期']==latest_date])) * 100
        st.metric("3000m 及格率", f"{pass_rate:.1f} %")

    with col_kpi3:
        # 計算引體向上相比上次的平均增減
        if len(all_dates) > 1:
            avg_now = df[df['測驗日期']==latest_date]['引體向上_下'].mean()
            avg_prev = df[df['測驗日期']==all_dates[1]]['引體向上_下'].mean()
            diff = avg_now - avg_prev
            st.metric("引體向上平均增減", f"{avg_now:.1f} 下", f"{diff:+.1f} 下")
        else:
            st.metric("引體向上平均", f"{df['引體向上_下'].mean():.1f} 下")

    with col_kpi4:
        st.metric("受測單位數", f"{df['分隊'].nunique()} 個分隊")

    # --- 4. 分頁系統 (Tabs) ---
    tab_overview, tab_group, tab_individual, tab_alert = st.tabs([
        "📊 大隊戰情總覽", "🔍 族群交叉分析", "🎯 個人追蹤儀表", "🚨 紅燈預警名單"
    ])

    # --- Tab 1: 大隊戰情總覽 ---
    with tab_overview:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("各分隊引體向上實力")
            fig_bar = px.bar(df.groupby('分隊')['引體向上_下'].mean().reset_index(), x='分隊', y='引體向上_下', color='分隊', text_auto='.1f')
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            st.subheader("大隊 3000m 歷次趨勢")
            trend = df.groupby('測驗日期')['3000公尺跑步_秒'].mean().reset_index()
            fig_line = px.line(trend, x='測驗日期', y='3000公尺跑步_秒', markers=True)
            fig_line.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_line, use_container_width=True)

    # --- Tab 2: 族群交叉分析 (年齡/性別/多選) ---
    with tab_group:
        f1, f2, f3, f4 = st.columns(4)
        with f1: s_gen = st.multiselect("性別", df['性別'].unique(), default=df['性別'].unique().tolist())
        with f2: s_age = st.multiselect("年齡層", df['年齡層'].dropna().unique().tolist(), default=df['年齡層'].dropna().unique().tolist())
        with f3: s_team = st.multiselect("分隊", df['分隊'].unique(), default=df['分隊'].unique().tolist())
        with f4: s_met = st.selectbox("分析項目", ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'])
        
        filtered = df[(df['性別'].isin(s_gen)) & (df['年齡層'].isin(s_age)) & (df['分隊'].isin(s_team))]
        if not filtered.empty:
            fig_box = px.box(filtered, x="分隊", y=s_met, color="性別", points="all", hover_data=['姓名'])
            if '秒' in s_met: fig_box.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.warning("請調整篩選條件，目前無符合資料。")

    # --- Tab 3: 個人追蹤儀表 ---
    with tab_individual:
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            p_name = st.selectbox("選擇隊員", df['姓名'].unique())
            p_data = df[df['姓名'] == p_name].sort_values(by='測驗日期', ascending=False).iloc[0]
            st.write(f"**最後受測日：** {p_data['測驗日期']}")
            st.write(f"**所屬單位：** {p_data['分隊']}")
        with col_p2:
            radar_df = pd.DataFrame({
                '項目': ['引體向上', '繩索救援', '3000m', '負重爬梯'],
                '分數': [min(p_data['引體向上_下']*6, 100), p_data['繩索救援_分數'], max(100-(p_data['3000公尺跑步_秒']-700)*0.1, 0), max(100-(p_data['負重爬梯_秒']-30)*1.5, 0)]
            })
            fig_radar = px.line_polar(radar_df, r='分數', theta='項目', line_close=True, range_r=[0, 100])
            fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
            st.plotly_chart(fig_radar, use_container_width=True)

    # --- Tab 4: 紅燈預警名單 (關鍵功能！) ---
    with tab_alert:
        st.subheader("🚨 訓練警示區")
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.markdown("**🔥 成績大幅退步名單** (3000m 較上次慢 30秒以上)")
            if len(all_dates) > 1:
                # 簡單計算兩次日期之間的差異
                d_latest = df[df['測驗日期']==all_dates[0]][['姓名', '分隊', '3000公尺跑步_秒']]
                d_prev = df[df['測驗日期']==all_dates[1]][['姓名', '3000公尺跑步_秒']]
                merged = pd.merge(d_latest, d_prev, on='姓名', suffixes=('_今', '_昨'))
                merged['退步秒數'] = merged['3000公尺跑步_秒_今'] - merged['3000公尺跑步_秒_昨']
                regression = merged[merged['退步秒數'] > 30].sort_values(by='退步秒數', ascending=False)
                if not regression.empty:
                    st.dataframe(regression[['姓名', '分隊', '退步秒數']], hide_index=True)
                else:
                    st.success("🎉 本次測驗無人大幅退步！")
            else:
                st.info("需要至少兩次測驗紀錄才能分析退步情況。")

        with col_a2:
            st.markdown("**❌ 本次未達標名單** (引體向上少於 6 下)")
            fail_list = df[(df['測驗日期']==latest_date) & (df['引體向上_下'] < 6)]
            if not fail_list.empty:
                st.dataframe(fail_list[['姓名', '分隊', '引體向上_下']], hide_index=True)
            else:
                st.success("🎉 全員引體向上皆達標！")
