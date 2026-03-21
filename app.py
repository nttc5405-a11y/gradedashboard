import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="成功消防大隊 - 體技能儀表板", page_icon="🚒", layout="wide")

#st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 18px; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)
    
st.markdown("""
    <style>
    /* 1. 全局數值與卡片樣式 */
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }

    /* 2. 重塑 Tab 容器：給予整體一個淺色背景與內距，看起來像按鈕列 */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 12px; 
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 12px;
    }

    /* 3. 個別 Tab 未選取時的預設按鈕外觀 */
    .stTabs [data-baseweb="tab"] { 
        height: 50px; 
        font-weight: bold; 
        font-size: 16px; 
        background-color: #ffffff;
        border-radius: 8px;
        padding: 0 20px;
        color: #555555;
        border: 1px solid #e0e0e0;
        transition: all 0.3s ease;
    }

    /* 4. 滑鼠懸停 (Hover) 時的微亮提示 */
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #ffeaea;
        color: #FF4B4B;
        border-color: #FF4B4B;
    }

    /* 5. 被選取的 Tab (Active) 呈現醒目的高光底色 */
    .stTabs [aria-selected="true"] {
        background-color: #FF4B4B !important;
        color: #ffffff !important;
        border-color: #FF4B4B !important;
        box-shadow: 0 4px 6px rgba(255, 75, 75, 0.3);
    }
    
    /* 隱藏預設的藍色底線 */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 成功消防大隊 - 體技能儀表板")

@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        df = pd.read_csv(url)
        
        last_valid_idx = df['姓名'].last_valid_index()
        if last_valid_idx is not None:
            df = df.iloc[:last_valid_idx + 2].copy()
            
        df = df.reset_index(drop=True)
        
        if '測驗日期' not in df.columns:
            df['測驗日期'] = '本次測驗'
            
        meta_cols = [c for c in df.columns if '合計' in c or '總成績' in c or '備註' in c]
        ffill_cols = ['NO.', '單位', '姓名', '性別', '年齡', '測驗日期'] + meta_cols
        
        existing_cols = [c for c in ffill_cols if c in df.columns]
        df[existing_cols] = df[existing_cols].ffill()
        
        df['資料類型'] = np.where(df.index % 2 == 0, '紀錄', '分數')
        
        KNOWN_COLS = ['NO.', '單位', '姓名', '性別', '年齡', '測驗日期', '資料類型', '年齡層']
        test_metrics = [c for c in df.columns if c not in KNOWN_COLS 
                        and '合計' not in c 
                        and '總成績' not in c 
                        and '備註' not in c 
                        and not str(c).startswith('Unnamed')]
        
        numeric_cols = test_metrics + meta_cols + ['年齡']
        for m in numeric_cols:
            if m in df.columns:
                df[m] = pd.to_numeric(df[m], errors='coerce')
        
        bins = [20, 30, 40, 50, 70]
        labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
        df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        
        return df, test_metrics, meta_cols
    except Exception as e:
        st.error(f"資料讀取失敗，請檢查。錯誤訊息：{e}")
        return None, [], []

df, test_metrics, meta_cols = load_and_clean_data()

if df is not None and len(test_metrics) > 0:
    all_dates = sorted(df['測驗日期'].dropna().unique(), reverse=True)
    latest_date = all_dates[0] if all_dates else '本次測驗'
    
    df_score = df[df['資料類型'] == '分數'].copy()
    df_record = df[df['資料類型'] == '紀錄'].copy()
    
    df_score_tested = df_score.dropna(subset=test_metrics, how='all')
    analysis_options = test_metrics + [c for c in meta_cols if '備註' not in c]
    
    k1, k2, k3, k4 = st.columns(4)
    latest_tested_df = df_score_tested[df_score_tested['測驗日期'] == latest_date]
    
    with k1: st.metric("本次實際測驗人數", f"{latest_tested_df['姓名'].nunique()} 人")
    with k2: st.metric("單項測驗數", f"{len(test_metrics)} 項")
    with k3: st.metric("受測單位數", f"{latest_tested_df['單位'].nunique()} 個")
    with k4: st.metric("最新測驗日期", f"{latest_date}")

    tab_overview, tab_group, tab_individual, tab_record, tab_alert = st.tabs([
        "📊 戰情總覽", "🔍 交叉分析", "🎯 個人雷達", "📝 紀錄查詢", "🚨 預警與進步榜"
    ])

    # --- Tab 1: 大隊戰情總覽 ---
    with tab_overview:
        selected_metric = st.selectbox("請選擇觀測項目 (皆呈現換算後的分數)：", analysis_options, key='ov_m')
        
        c1, c2 = st.columns(2)
        with c1:
            avg_df = latest_tested_df.groupby('單位')[selected_metric].mean().reset_index()
            fig_bar = px.bar(avg_df, x='單位', y=selected_metric, color='單位', text_auto='.1f', 
                             title=f"各單位 {selected_metric} 平均得分 ({latest_date})")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with c2:
            trend_df = df_score_tested.groupby('測驗日期')[selected_metric].mean().reset_index()
            # 魔法 1：如果測驗次數不足兩次，自動切換為分數分布直方圖
            if len(trend_df) > 1:
                fig_line = px.line(trend_df, x='測驗日期', y=selected_metric, markers=True, 
                                   title=f"大隊 {selected_metric} 歷次平均得分趨勢")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                fig_hist = px.histogram(latest_tested_df, x=selected_metric, nbins=10, 
                                        title=f"大隊 {selected_metric} 得分分布區間 ({latest_date})",
                                        color_discrete_sequence=['#FF4B4B'])
                fig_hist.update_layout(yaxis_title="人數")
                st.plotly_chart(fig_hist, use_container_width=True)

    # --- Tab 2: 族群交叉分析 ---
    with tab_group:
        st.subheader("🕵️ 多維度族群交叉篩選 (分析得分分布)")
        f1, f2, f3, f4, f5 = st.columns(5)
        
        with f1: s_date = st.multiselect("測驗日期", all_dates, default=[latest_date])
        with f2: s_gen = st.multiselect("性別", df_score_tested['性別'].dropna().unique(), default=df_score_tested['性別'].dropna().unique().tolist())
        with f3: s_age = st.multiselect("年齡層", df_score_tested['年齡層'].dropna().unique().tolist(), default=df_score_tested['年齡層'].dropna().unique().tolist())
        with f4: s_team = st.multiselect("單位", df_score_tested['單位'].dropna().unique(), default=df_score_tested['單位'].dropna().unique().tolist())
        with f5: s_met = st.selectbox("分析項目", analysis_options, key='gr_m')
        
        filtered = df_score_tested[
            (df_score_tested['測驗日期'].isin(s_date)) & 
            (df_score_tested['性別'].isin(s_gen)) & 
            (df_score_tested['年齡層'].isin(s_age)) & 
            (df_score_tested['單位'].isin(s_team))
        ]
        
        if not filtered.empty:
            fig_box = px.box(filtered, x="單位", y=s_met, color="性別", points="all", hover_data=['姓名', '測驗日期'])
            st.plotly_chart(fig_box, use_container_width=True)
            st.info(f"📌 此條件下共篩選出 {len(filtered)} 筆有效得分紀錄。")
        else:
            st.warning("⚠️ 找不到符合篩選條件的資料，請放寬限制。")

    # --- Tab 3: 個人追蹤儀表 (雷達圖) ---
    with tab_individual:
        st.subheader("🎯 個人得分 PR 值雷達圖與常模對比")
        sel_c1, sel_c2 = st.columns(2)
        with sel_c1:
            radar_unit = st.selectbox("1️⃣ 選擇單位", df['單位'].dropna().unique(), key='radar_unit')
        with sel_c2:
            radar_names = df[df['單位'] == radar_unit]['姓名'].dropna().unique()
            p_name = st.selectbox("2️⃣ 選擇隊員", radar_names, key='radar_name')
            
        cp1, cp2 = st.columns([1, 2])
        with cp1:
            p_scores = df_score[df_score['姓名'] == p_name].sort_values(by='測驗日期', ascending=False)
            p_records = df_record[df_record['姓名'] == p_name].sort_values(by='測驗日期', ascending=False)
            
            if not p_scores.empty and not p_records.empty:
                p_score_latest = p_scores.iloc[0]
                p_record_latest = p_records.iloc[0]
                p_age_group = p_score_latest['年齡層']
                
                st.info(f"姓名： {p_score_latest['姓名']} | 單位： {p_score_latest['單位']} | 年齡層： {p_age_group}")
                
                # 魔法 2：計算同齡層常模平均
                age_group_df = latest_tested_df[latest_tested_df['年齡層'] == p_age_group]
                
                st.write(f"**{latest_date}** 最新明細 (紀錄 / 分數)：")
                for m in test_metrics:
                    rec_val = p_record_latest[m] if pd.notna(p_record_latest[m]) else "-"
                    score_val = p_score_latest[m] if pd.notna(p_score_latest[m]) else "-"
                    
                    # 取出同齡平均分數
                    age_avg = age_group_df[m].mean() if not age_group_df.empty else None
                    age_avg_text = f" | 同齡平均: {age_avg:.1f}分" if age_avg and pd.notna(age_avg) else ""
                    
                    st.write(f"- **{m}**： {rec_val} / 得 {score_val} 分 <span style='color:gray; font-size:14px;'>{age_avg_text}</span>", unsafe_allow_html=True)
                    
        with cp2:
            if not p_scores.empty:
                radar_scores = []
                valid_metrics = []
                
                for m in test_metrics:
                    val = p_score_latest[m]
                    if pd.notna(val):
                        latest_all = latest_tested_df[m].dropna()
                        if len(latest_all) > 0:
                            pr = (latest_all <= val).mean() * 100
                            radar_scores.append(pr)
                            valid_metrics.append(m)

                if len(valid_metrics) > 2:
                    radar_df = pd.DataFrame({'項目': valid_metrics, 'PR值 (大隊百分等級)': radar_scores})
                    fig_radar = px.line_polar(radar_df, r='PR值 (大隊百分等級)', theta='項目', line_close=True, range_r=[0, 100])
                    fig_radar.update_traces(fill='toself', line_color='#1E90FF')
                    fig_radar.update_layout(polar=dict(radialaxis=dict(showticklabels=False))) # 隱藏雷達圖雜亂刻度
                    st.plotly_chart(fig_radar, use_container_width=True)
                else:
                    st.warning("該員有效成績項目不足，無法繪製雷達圖。")

    # --- Tab 4: 個人紀錄查詢 ---
    with tab_record:
        st.subheader("📝 個人歷次測驗紀錄查詢 (原始數據：次數 / 秒數)")
        rc1, rc2 = st.columns(2)
        with rc1: rec_unit = st.selectbox("1️⃣ 選擇單位", df['單位'].dropna().unique(), key='rec_unit')
        with rc2: 
            rec_names = df[df['單位'] == rec_unit]['姓名'].dropna().unique()
            rec_name = st.selectbox("2️⃣ 選擇隊員", rec_names, key='rec_name')
            
        p_records_all = df_record[df_record['姓名'] == rec_name].sort_values(by='測驗日期', ascending=False)
        
        if not p_records_all.empty:
            display_cols = ['測驗日期'] + test_metrics
            st.markdown(f"##### 📋 {rec_name} - 歷次成績總表")
            st.dataframe(p_records_all[display_cols], hide_index=True, use_container_width=True)
            
            st.markdown("##### 📈 單項歷次紀錄趨勢")
            rec_metric = st.selectbox("請選擇觀測的測驗項目：", test_metrics, key='rec_metric')
            plot_data = p_records_all.dropna(subset=[rec_metric]).sort_values(by='測驗日期')
            
            if not plot_data.empty:
                fig_rec = px.line(plot_data, x='測驗日期', y=rec_metric, markers=True, text=rec_metric)
                fig_rec.update_traces(textposition="top center")
                
                if '秒' in rec_metric:
                    fig_rec.update_yaxes(autorange="reversed")
                    fig_rec.update_layout(title=f"{rec_name} - {rec_metric} 歷次紀錄 (秒數越少越佳)")
                else:
                    fig_rec.update_layout(title=f"{rec_name} - {rec_metric} 歷次紀錄 (次數/公分越多越佳)")
                st.plotly_chart(fig_rec, use_container_width=True)
            else:
                st.info(f"該員尚無 {rec_metric} 的測驗紀錄。")

    # --- Tab 5: 預警與進步榜 ---
    with tab_alert:
        ca1, ca2, ca3 = st.columns(3) # 切成三欄，加入進步榜
        
        with ca1:
            st.markdown("##### ❌ 自訂未達標監控")
            fail_m = st.selectbox("監控達標項目 (分數)：", analysis_options, key='al_f1')
            fail_val = st.number_input("最低及格標準：", value=60)
            
            fail_list = latest_tested_df[latest_tested_df[fail_m] < fail_val]
            if not fail_list.empty:
                # 魔法 3：紅燈警示 (套用 pandas style)
                st.dataframe(fail_list[['姓名', '單位', fail_m]].style.map(
                    lambda x: 'background-color: #ffcccc; color: black;' if isinstance(x, (int, float)) and x < fail_val else '', subset=[fail_m]
                ), hide_index=True, use_container_width=True)
            else:
                st.success("🎉 本次測驗全員通過！")

        with ca2:
            st.markdown("##### 🔥 退步輔導名單")
            reg_m = st.selectbox("監控退步項目 (分數)：", analysis_options, key='al_r1')
            reg_val = st.number_input("容許退步空間 (減少幾分)：", value=10)
            
            if len(all_dates) > 1:
                d_now = latest_tested_df[['姓名', '單位', reg_m]]
                d_old = df_score_tested[df_score_tested['測驗日期']==all_dates[1]][['姓名', reg_m]]
                merged = pd.merge(d_now, d_old, on='姓名', suffixes=('_今', '_昨')).dropna()
                
                merged['退步幅度'] = merged[f'{reg_m}_昨'] - merged[f'{reg_m}_今']
                regression = merged[merged['退步幅度'] > reg_val].sort_values(by='退步幅度', ascending=False)
                
                if not regression.empty:
                    st.dataframe(regression[['姓名', '單位', '退步幅度']], hide_index=True, use_container_width=True)
                else:
                    st.success("🎉 無人觸發退步警示！")
            else:
                st.info("資料不足兩次測驗。")

        with ca3:
            st.markdown("##### 🏆 最佳進步榜")
            prog_m = st.selectbox("觀察進步項目 (分數)：", analysis_options, key='al_p1')
            prog_val = st.number_input("顯示進步超過幾分：", value=5)
            
            if len(all_dates) > 1:
                # 魔法 4：計算進步幅度
                d_now = latest_tested_df[['姓名', '單位', prog_m]]
                d_old = df_score_tested[df_score_tested['測驗日期']==all_dates[1]][['姓名', prog_m]]
                merged = pd.merge(d_now, d_old, on='姓名', suffixes=('_今', '_昨')).dropna()
                
                merged['進步幅度'] = merged[f'{prog_m}_今'] - merged[f'{prog_m}_昨']
                progress = merged[merged['進步幅度'] >= prog_val].sort_values(by='進步幅度', ascending=False)
                
                if not progress.empty:
                    # 綠燈表揚
                    st.dataframe(progress[['姓名', '單位', '進步幅度']].style.map(
                        lambda x: 'background-color: #ccffcc; color: black;' if isinstance(x, (int, float)) and x >= prog_val else '', subset=['進步幅度']
                    ), hide_index=True, use_container_width=True)
                else:
                    st.info("目前無人達到設定的進步門檻。")
            else:
                st.info("資料不足兩次測驗。")
else:
    st.info("等待讀取資料庫...")
