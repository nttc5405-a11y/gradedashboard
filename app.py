import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="成功消防大隊 - 體技能儀表板", page_icon="🚒", layout="wide")
st.title("🚒 成功消防大隊 - 體技能成績分析看板")

# --- 2. 串接 Google Sheets 資料 ---
# ⚠️ 請將下方的網址換成您自己發布的 CSV 網址！
# 改成從 Streamlit 的 Secrets 密碼本裡面讀取
sheet_url = st.secrets["sheet_url"]

@st.cache_data(ttl=60)
def load_data(url):
    df = pd.read_csv(url)
    # 確保日期格式為字串，方便畫趨勢圖
    df['測驗日期'] = df['測驗日期'].astype(str)
    return df

try:
    df = load_data(sheet_url)
    st.success("✅ 成功連線至 Google Sheets 資料庫！")
    
    with st.expander("👀 點我查看/隱藏原始成績單"):
        st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # --- 3. 大隊整體分析 (上排圖表：長條圖 與 折線圖) ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 各分隊【引體向上】平均成績比較")
        avg_pullups = df.groupby('分隊')['引體向上_下'].mean().reset_index()
        fig_bar = px.bar(avg_pullups, x='分隊', y='引體向上_下', color='分隊', text_auto='.1f')
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("📈 大隊【3000公尺】歷次成績趨勢")
        st.markdown("<span style='font-size:14px; color:gray;'>*註：折線圖往下代表秒數減少 (進步)*</span>", unsafe_allow_html=True)
        # 計算每次測驗的 3000m 平均秒數
        trend_data = df.groupby('測驗日期')['3000公尺跑步_秒'].mean().reset_index()
        fig_line = px.line(trend_data, x='測驗日期', y='3000公尺跑步_秒', markers=True)
        # 因為跑步秒數越低越好，所以我們把 Y 軸反轉
        fig_line.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")

    # --- 4. 分隊實力分布分析 (中排圖表：盒鬚圖) ---
    st.subheader("📦 各分隊【負重爬梯】實力分布 (盒鬚圖)")
    st.markdown("<span style='font-size:14px; color:gray;'>*💡 教官看圖訣竅：盒子越扁代表該分隊實力越平均；圖上的單獨小點代表特別快或特別慢的人員。*</span>", unsafe_allow_html=True)
    
    fig_box = px.box(df, x="分隊", y="負重爬梯_秒", color="分隊", points="all")
    st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("---")

    # --- 5. 個人體能雷達圖 (下排圖表) ---
    st.subheader("🎯 個人體技能綜合評估 (雷達圖)")

    col_person1, col_person2 = st.columns([1, 2])

    with col_person1:
        selected_team = st.selectbox("請選擇分隊", df['分隊'].unique())
        team_members = df[df['分隊'] == selected_team]['姓名'].unique()
        selected_person = st.selectbox("請選擇人員", team_members)

    with col_person2:
        # 抓出這位弟兄的最新一筆成績
        person_data = df[df['姓名'] == selected_person].sort_values(by='測驗日期', ascending=False).iloc[0]
        
        # 分數轉換 (將各項指標轉成 0~100 的相對分數，僅為視覺化範例)
        score_pullup = min(person_data['引體向上_下'] * 6, 100) 
        score_rope = person_data['繩索救援_分數']
        score_run = max(100 - (person_data['3000公尺跑步_秒'] - 700) * 0.1, 0) 
        score_climb = max(100 - (person_data['負重爬梯_秒'] - 30) * 1.5, 0) 
        
        radar_df = pd.DataFrame({
            '評估項目': ['引體向上肌力', '繩索救援技術', '3000m心肺耐力', '負重爬梯爆發力'],
            '分數': [score_pullup, score_rope, score_run, score_climb]
        })
        
        fig_radar = px.line_polar(radar_df, r='分數', theta='評估項目', line_close=True, range_r=[0, 100], markers=True)
        fig_radar.update_traces(fill='toself', line_color='#FF4B4B') 
        st.plotly_chart(fig_radar, use_container_width=True)

except Exception as e:
    st.error(f"連線或處理資料時發生錯誤：{e}")
