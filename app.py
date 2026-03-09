import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="成功消防大隊 - 戰情室 2.1", page_icon="🚒", layout="wide")

# CSS 美化介面
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 18px; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能科學化訓練戰情室 2.1")

# --- 2. 資料讀取與預處理 ---
@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        # 從 Streamlit Secrets 讀取隱藏的 Google Sheets 網址
        url = st.secrets["sheet_url"]
        df = pd.read_csv(url)
        
        # 資料清洗：將各項成績轉為數字，非數字(如公假)會轉為 NaN 避免計算出錯
        metrics = ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數']
        for m in metrics:
            df[m] = pd.to_numeric(df[m], errors='coerce')
        
        # 自動產生年齡分層
        bins = [20, 30, 40, 50, 70]
        labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
        df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        
        # 排序：確保日期與姓名順序正確，方便計算趨勢
        df = df.sort_values(by=['姓名', '測驗日期'])
        return df
    except Exception as e:
        st.error(f"資料讀取失敗，請檢查 Secrets 與 Google Sheets 設定。錯誤訊息：{e}")
        return None

df = load_and_clean_data()

# --- 3. 進入戰情室主要邏輯 ---
if df is not None:
    # 取得最新與次新的測驗日期
    all_dates = sorted(df['測驗日期'].unique(), reverse=True)
    latest_date = all_dates[0]
    
    # --- 頂部戰情指標區 (KPI) ---
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("本次測驗總人數", f"{len(df[df['測驗日期']==latest_date])} 人")
    with k2:
        # 假設 3000m 標竿為 14:30 (870秒)
        pass_run = df[(df['測驗日期']==latest_date) & (df['3000公尺跑步_秒'] <= 870)]
        st.metric("3000m 及格率", f"{(len(pass_run)/len(df[df['測驗日期']==latest_date])*100):.1f} %")
    with k3:
        if len(all_dates) > 1:
            avg_now = df[df['測驗日期']==latest_date]['引體向上_下'].mean()
            avg_prev = df[df['測驗日期']==all_dates[1]]['引體向上_下'].mean()
            diff = avg_now - avg_prev
            st.metric("引體向上大隊平均", f"{avg_now:.1f} 下", f"{diff:+.1f} 下")
    with k4:
        st.metric("受測分隊數", f"{df['分隊'].nunique()} 個")

    # --- 分頁系統 ---
    tab_overview, tab_group, tab_individual, tab_alert = st.tabs([
        "📊 大隊戰情總覽", "🔍 族群交叉分析", "🎯 個人追蹤儀表", "🚨 訓練警示區"
    ])

    # --- Tab 1: 大隊戰情總覽 ---
    with tab_overview:
        st.subheader("📈 大隊績效趨勢與比較")
        selected_metric = st.selectbox("請選擇欲觀測項目：", ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'], key='ov_m')
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**各分隊平均表現**")
            avg_df = df.groupby('分隊')[selected_metric].mean().reset_index()
            fig_bar = px.bar(avg_df, x='分隊', y=selected_metric, color='分隊', text_auto='.1f')
            if '秒' in selected_metric: fig_bar.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            st.markdown(f"**大隊歷次趨勢**")
            trend_df = df.groupby('測驗日期')[selected_metric].mean().reset_index()
            fig_line = px.line(trend_df, x='測驗日期', y=selected_metric, markers=True)
            if '秒' in selected_metric: fig_line.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_line, use_container_width=True)

    # --- Tab 2: 族群交叉分析 ---
    with tab_group:
        st.subheader("🕵️ 多維度族群交叉篩選")
        f1, f2, f3, f4 = st.columns(4)
        with f1: s_gen = st.multiselect("性別", df['性別'].unique(), default=df['性別'].unique().tolist())
        with f2: s_age = st.multiselect("年齡層", df['年齡層'].dropna().unique().tolist(), default=df['年齡層'].dropna().unique().tolist())
        with f3: s_team = st.multiselect("分隊", df['分隊'].unique(), default=df['分隊'].unique().tolist())
        with f4: s_met = st.selectbox("分析項目", ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'], key='gr_m')
        
        filtered = df[(df['性別'].isin(s_gen)) & (df['年齡層'].isin(s_age)) & (df['分隊'].isin(s_team))]
        if not filtered.empty:
            fig_box = px.box(filtered, x="分隊", y=s_met, color="性別", points="all", hover_data=['姓名', '測驗日期'])
            if '秒' in s_met: fig_box.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.warning("⚠️ 找不到符合篩選條件的資料，請放寬限制。")

    # --- Tab 3: 個人追蹤儀表 ---
    with tab_individual:
        st.subheader("🎯 隊員個人體技能履歷")
        cp1, cp2 = st.columns([1, 2])
        with cp1:
            p_name = st.selectbox("選擇隊員", df['姓名'].unique())
            person_all_data = df[df['姓名'] == p_name].sort_values(by='測驗日期', ascending=False)
            p_latest = person_all_data.iloc[0]
            st.info(f"**姓名：** {p_latest['姓名']}  \n**單位：** {p_latest['分隊']}  \n**性別：** {p_latest['性別']}  \n**最後受測：** {p_latest['測驗日期']}")
            
            # 顯示個人成績明細
            st.write("**最新測驗成績：**")
            st.write(f"- 3000m跑步：{p_latest['3000公尺跑步_秒']} 秒")
            st.write(f"- 引體向上：{p_latest['引體向上_下']} 下")
        with cp2:
            radar_df = pd.DataFrame({
                '項目': ['引體向上', '繩索救援', '3000m', '負重爬梯'],
                '分數': [
                    min(p_latest['引體向上_下']*6.5, 100), 
                    p_latest['繩索救援_分數'], 
                    max(100-(p_latest['3000公尺跑步_秒']-700)*0.1, 0), 
                    max(100-(p_latest['負重爬梯_秒']-30)*1.5, 0)
                ]
            })
            fig_radar = px.line_polar(radar_df, r='分數', theta='項目', line_close=True, range_r=[0, 100])
            fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
            st.plotly_chart(fig_radar, use_container_width=True)

    # --- Tab 4: 訓練警示區 (紅燈名單) ---
    with tab_alert:
        st.subheader("🚨 訓練弱點監控")
        ca1, ca2 = st.columns(2)
        
        with ca1:
            st.markdown("##### 🔥 成績大幅退步名單 \n*(3000m 較上次測驗慢 30秒以上)*")
            if len(all_dates) > 1:
                d_now = df[df['測驗日期']==all_dates[0]][['姓名', '分隊', '3000公尺跑步_秒']]
                d_old = df[df['測驗日期']==all_dates[1]][['姓名', '3000公尺跑步_秒']]
                merged = pd.merge(d_now, d_old, on='姓名', suffixes=('_今', '_昨'))
                merged['退步秒數'] = merged['3000公尺跑步_秒_今'] - merged['3000公尺跑步_秒_昨']
                regression = merged[merged['退步秒數'] > 30].sort_values(by='退步秒數', ascending=False)
                
                if not regression.empty:
                    st.dataframe(regression[['姓名', '分隊', '退步秒數']], hide_index=True, use_container_width=True)
                else:
                    st.success("🎉 本次測驗大隊體力維持良好，無人大幅退步！")
            else:
                st.info("需要至少兩次測驗紀錄才能進行退步分析。")

        with ca2:
            st.markdown("##### ❌ 本次未達標名單 \n*(引體向上少於 6 下)*")
            fail_list = df[(df['測驗日期']==latest_date) & (df['引體向上_下'] < 6)]
            
            if not fail_list.empty:
                st.dataframe(fail_list[['姓名', '分隊', '引體向上_下']], hide_index=True, use_container_width=True)
            else:
                st.success("🎉 全員引體向上皆在及格標準以上！")
