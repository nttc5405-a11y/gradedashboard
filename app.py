import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="成功消防大隊 - 戰情室 2.1", page_icon="🚒", layout="wide")

# CSS 美化指標卡與分頁
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能科學化訓練戰情室 2.1")

# --- 2. 串接與資料預處理 ---
@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        df = pd.read_csv(url)
        
        # 資料清洗：將成績轉為數字，忽略非數字文字
        metrics = ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數']
        for m in metrics:
            df[m] = pd.to_numeric(df[m], errors='coerce')
        
        # 年齡分層
        bins = [20, 30, 40, 50, 65]
        labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
        df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        
        # 排序
        df = df.sort_values(by=['姓名', '測驗日期'])
        return df
    except Exception as e:
        st.error(f"資料讀取錯誤：{e}")
        return None

df = load_and_clean_data()

# --- 進入主要邏輯 (所有的程式碼都必須在這個 if 區塊內縮進) ---
if df is not None:
    # 3. 戰情指標區 (KPI)
    all_dates = sorted(df['測驗日期'].unique(), reverse=True)
    latest_date = all_dates[0]
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("本次測驗總人數", f"{len(df[df['測驗日期']==latest_date])} 人")
    with k2:
        pass_run = df[(df['測驗日期']==latest_date) & (df['3000公尺跑步_秒'] <= 870)]
        st.metric("3000m 及格率", f"{(len(pass_run)/len(df[df['測驗日期']==latest_date])*100):.1f} %")
    with k3:
        if len(all_dates) > 1:
            diff = df[df['測驗日期']==latest_date]['引體向上_下'].mean() - df[df['測驗日期']==all_dates[1]]['引體向上_下'].mean()
            st.metric("引體向上平均增減", f"{df[df['測驗日期']==latest_date]['引體向上_下'].mean():.1f} 下", f"{diff:+.1f} 下")
    with k4: st.metric("受測單位數", f"{df['分隊'].nunique()} 個分隊")

    # 4. 分頁系統
    tab_overview, tab_group, tab_individual, tab_alert = st.tabs([
        "📊 大隊戰情總覽", "🔍 族群交叉分析", "🎯 個人追蹤儀表", "🚨 紅燈預警名單"
    ])

    # --- Tab 1: 大隊戰情總覽 (優化版) ---
    with tab_overview:
        st.subheader("📊 大隊訓練績效總覽")
        selected_metric = st.selectbox("請選擇測驗項目：", ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'], key='ov_m')
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**各分隊 {selected_metric} 平均表現**")
            avg_data = df.groupby('分隊')[selected_metric].mean().reset_index()
            fig_bar = px.bar(avg_data, x='分隊', y=selected_metric, color='分隊', text_auto='.1f')
            if '秒' in selected_metric: fig_bar.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            st.markdown(f"**大隊 {selected_metric} 歷次趨勢**")
            trend = df.groupby('測驗日期')[selected_metric].mean().reset_index()
            fig_line = px.line(trend, x='測驗日期', y=selected_metric, markers=True)
            if '秒' in selected_metric: fig_line.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_line, use_container_width=True)

    # --- Tab 2: 族群交叉分析 ---
    with tab_group:
        f1, f2, f3, f4 = st.columns(4)
        with f1: s_gen = st.multiselect("性別", df['性別'].unique(), default=df['性別'].unique().tolist())
        with f2: s_age = st.multiselect("年齡層", df['年齡層'].dropna().unique().tolist(), default=df['年齡層'].dropna().unique().tolist())
        with f3: s_team = st.multiselect("分隊", df['分隊'].unique(), default=df['分隊'].unique().tolist())
        with f4: s_met = st.selectbox("分析項目", ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'], key='gr_m')
        
        filtered = df[(df['性別'].isin(s_gen)) & (df['年齡層'].isin(s_age)) & (df['分隊'].isin(s_team))]
        if not filtered.empty:
            fig_box = px.box(filtered, x="分隊", y=s_met, color="性別", points="all", hover_data=['姓名'])
            if '秒' in s_met: fig_box.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_box, use_container_width=True)

    # --- Tab 3: 個人追蹤儀表 ---
    with tab_individual:
        cp1, cp2 = st.columns([1, 2])
        with cp1:
            p_name = st.selectbox("選擇隊員", df['姓名'].unique())
            p_data = df[df['姓名'] == p_name].sort_values(by='測驗日期', ascending=False).iloc[0]
            st.info(f"單位：{p_data['分隊']} | 最後受測：{p_data['測驗日期']}")
        with cp2:
            radar_df = pd.DataFrame({
                '項目': ['引體向上', '繩索救援', '3000m', '負重爬梯'],
                '分數': [min(p_data['引體向上_下']*6, 100), p_data['繩索救援_分數'], max(100-(p_data['3000公尺跑步_秒']-700)*0.1, 0), max(100-(p_data['負重爬梯_秒']-30)*1.5, 0)]
            })
            fig_radar = px.line_polar(radar_df, r='分數', theta='項目', line_close=True, range_r=[0, 100])
            fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
            st.plotly_chart(fig_radar, use_container_width=True)

    # --- Tab 4: 紅燈預警名單 ---
    with tab_alert:
        st.subheader("🚨 訓練警示區")
        ca1, ca2 = st.columns(2)
        with ca1:
            st.markdown("**🔥 成績大幅退步名單** (3000m 較上次慢 30s+)")
            if len(all_dates) > 1:
                d_l = df[df['測驗日期']==latest_date][['姓名', '分隊', '3000公尺跑步_秒']]
                d_p = df[df['測驗日期']==all_dates[1]][['姓名', '3000公尺跑步_秒']]
                m = pd.merge(d_l, d_p, on='姓名', suffixes=('_今', '_昨'))
                m['退步秒數'] = m['3000公尺跑步_秒_今'] - m['3000公尺跑步_秒_昨']
                reg = m[m['退步秒數'] > 30].sort_values(by='退步秒數', ascending=False)
                st.dataframe(reg[['姓名', '分隊', '退步秒數']], hide_index=True) if not reg.empty else st.success("無人大幅退步！")
        with ca2:
            st.markdown("**❌ 本次未達標名單** (引體向上 < 6下)")
            fail = df[(df['測驗日期']==latest_date) & (df['引體向上_下'] < 6)]
            st.dataframe(fail[['姓名', '分隊', '引體向上_下']], hide_index=True) if not fail.empty else st.success("全員達標！")
