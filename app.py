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
# ==========================================
# 以下為新增的進階分析區塊，請貼在程式碼最下方
# ==========================================

# --- 6. 進階群體分析 (年齡層與性別差異) ---
st.markdown("---")
st.subheader("🔍 進階群體分析 (年齡與性別差異)")

# 利用 Pandas 將年齡分組 (自動把年齡轉換成對應的年齡層標籤)
bins = [20, 30, 40, 50, 65]
labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)

col3, col4 = st.columns(2)

with col3:
    st.markdown("**各年齡層在測驗項目的表現差異**")
    age_metric = st.selectbox("請選擇測驗項目 (年齡分析)", ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'], key='age_metric')
    
    # 畫出年齡層的盒鬚圖
    fig_age = px.box(df, x="年齡層", y=age_metric, color="年齡層", category_orders={"年齡層": labels})
    
    # 如果是計時項目(秒)，Y軸反轉(越低越好)
    if '秒' in age_metric:
        fig_age.update_yaxes(autorange="reversed") 
    st.plotly_chart(fig_age, use_container_width=True)

with col4:
    st.markdown("**男女在各項目的平均差異**")
    # 檢查試算表中是否已經加入了「性別」欄位
    if '性別' in df.columns:
        gender_metric = st.selectbox("請選擇測驗項目 (性別分析)", ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'], key='gender_metric')
        
        # 畫出男女差異的盒鬚圖
        fig_gender = px.box(df, x="性別", y=gender_metric, color="性別")
        if '秒' in gender_metric:
            fig_gender.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gender, use_container_width=True)
    else:
        # 如果試算表還沒加性別欄位，顯示友善的提醒
        st.warning("⚠️ 查無「性別」欄位。請先在 Google Sheets 中新增「性別」欄位（填入男/女），此圖表便會自動出現！")


# --- 7. 個人歷年成績隨時間之變化 ---
st.markdown("---")
st.subheader("⏳ 個人成績隨時間變化軌跡")
st.markdown("<span style='font-size:14px; color:gray;'>*💡 選擇人員與項目，觀察長期的進步或退步趨勢。時間/秒數類測驗，折線往下代表進步！*</span>", unsafe_allow_html=True)

col_trend1, col_trend2 = st.columns([1, 3])

with col_trend1:
    trend_person = st.selectbox("請選擇要追蹤的人員", df['姓名'].unique(), key='trend_person')
    trend_metric = st.selectbox("請選擇要追蹤的測驗項目", ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'], key='trend_metric')

with col_trend2:
    # 篩選出該名人員的所有歷史紀錄，並依時間排序
    person_history = df[df['姓名'] == trend_person].sort_values(by='測驗日期')
    
    # 至少要有兩筆以上的資料才能畫趨勢線
    if len(person_history) > 1:
        fig_person_trend = px.line(person_history, x='測驗日期', y=trend_metric, markers=True, text=trend_metric)
        fig_person_trend.update_traces(textposition="bottom right") # 把數值顯示在點的右下方
        
        if '秒' in trend_metric:
            fig_person_trend.update_yaxes(autorange="reversed")
            
        st.plotly_chart(fig_person_trend, use_container_width=True)
    else:
        # 如果只有一筆資料，顯示提示訊息
        st.info(f"📊 **{trend_person}** 目前只有一筆測驗紀錄，尚無法畫出趨勢線。等下次測驗成績輸入後就會自動出現囉！")
# --- 8. 多重條件交叉分析 (終極篩選器) ---
st.markdown("---")
st.subheader("🎯 終極交叉分析：多重條件自訂篩選")
st.markdown("<span style='font-size:14px; color:gray;'>*💡 請在下方選擇您想觀察的特定族群，系統會即時撈出資料並繪製分布圖。*</span>", unsafe_allow_html=True)

# 建立四個並排的欄位放篩選器
col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    # 1. 性別篩選 (預設全選)
    gender_options = df['性別'].unique().tolist()
    selected_genders = st.multiselect("1. 選擇性別", gender_options, default=gender_options)

with col_f2:
    # 2. 年齡層篩選 (預設全選，排除空值)
    # 確保前面已經有執行 pd.cut 產生 '年齡層' 欄位
    age_options = df['年齡層'].dropna().unique().tolist()
    selected_ages = st.multiselect("2. 選擇年齡層", age_options, default=age_options)

with col_f3:
    # 3. 單位/分隊篩選 (預設全選)
    team_options = df['分隊'].unique().tolist()
    selected_teams = st.multiselect("3. 選擇單位", team_options, default=team_options)

with col_f4:
    # 4. 測驗項目 (單選)
    test_metric = st.selectbox("4. 選擇分析項目", ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'], key='multi_metric')

# --- 根據篩選條件過濾資料 (核心邏機) ---
# 使用 Pandas 的 isin() 函數來比對使用者選了哪些東西
filtered_df = df[
    (df['性別'].isin(selected_genders)) &
    (df['年齡層'].isin(selected_ages)) &
    (df['分隊'].isin(selected_teams))
]

# --- 繪製多重篩選後的結果圖表 ---
if filtered_df.empty:
    # 防呆機制：如果使用者把條件縮得太小（例如選了某個分隊但該分隊剛好沒有女性），導致沒有資料
    st.warning("⚠️ 在目前的篩選條件下，找不到任何符合的測驗紀錄。請嘗試放寬篩選條件！")
else:
    # 畫出盒鬚圖，X軸為分隊，顏色區分性別，滑鼠移過去可以看到每個點(人員)的詳細資料
    fig_multi = px.box(
        filtered_df, 
        x="分隊", 
        y=test_metric, 
        color="性別", 
        points="all", 
        hover_data=['姓名', '年齡', '測驗日期'], # 滑鼠移到點上會顯示姓名和年齡！
        title=f"自訂篩選結果：{test_metric} 分布狀況"
    )
    
    # 如果是計時項目(秒)，Y軸反轉(越低越好)
    if '秒' in test_metric:
        fig_multi.update_yaxes(autorange="reversed")
        
    st.plotly_chart(fig_multi, use_container_width=True)
    
    # 貼心小功能：在圖表下方顯示目前篩選出的總人數與平均值
    avg_score = filtered_df[test_metric].mean()
    st.info(f"📌 **分析結果摘要**：在目前的篩選條件下，共有 **{len(filtered_df)} 筆** 測驗紀錄。該族群在【{test_metric}】的整體平均成績為 **{avg_score:.1f}**。")
