import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="成功消防大隊 - 體技能儀表板 3.0", page_icon="🚒", layout="wide")

# --- 進階實體按鈕樣式與版面設計 ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #f8f9fa; padding: 10px; border-radius: 12px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 16px; background-color: #ffffff; border-radius: 8px; padding: 0 20px; color: #555555; border: 1px solid #e0e0e0; transition: all 0.3s ease; }
    .stTabs [data-baseweb="tab"]:hover { background-color: #ffeaea; color: #FF4B4B; border-color: #FF4B4B; }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; color: #ffffff !important; border-color: #FF4B4B !important; box-shadow: 0 4px 6px rgba(255, 75, 75, 0.3); }
    .stTabs [data-baseweb="tab-highlight"] { background-color: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 消防體技能儀表板")

@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQcsv0lMJmU68FYuyXRY6H4T9j9j8xgaC9xnSWwrCGbSuqACG1geXM34e-nvimhVQ/pub?gid=1434005373&single=true&output=csv"
        raw_df = pd.read_csv(sheet_url, header=None, skiprows=1)
        
        main_headers = raw_df.iloc[0].ffill() 
        sub_headers = raw_df.iloc[1].fillna('')
        
        new_cols = []
        for m, s in zip(main_headers, sub_headers):
            m = str(m).strip()
            s = str(s).strip()
            if m.startswith('Unnamed') or m == 'nan': m = ''
            if s.startswith('Unnamed') or s == 'nan': s = ''
            
            if any(keyword in s for keyword in ['姓名', '大隊', '分隊', '單位', '性別', '年齡', '日期', '分數總和']):
                new_cols.append(s)
            elif m and s and m != s:
                new_cols.append(f"{m}_{s}")
            elif m:
                new_cols.append(m)
            else:
                new_cols.append(s)
                
        df = raw_df.iloc[2:].copy()
        df.columns = new_cols
        df = df.reset_index(drop=True)
        
        df = df.loc[:, ~df.columns.duplicated()]
        
        rename_map = {}
        for c in df.columns:
            c_str = str(c)
            if ('大隊' in c_str or '所屬單位' in c_str) and '所屬大隊' not in c_str: 
                rename_map[c] = '所屬大隊'
            elif '分隊' in c_str and '單位' not in c_str: 
                rename_map[c] = '單位'
        df = df.rename(columns=rename_map)
        
        if '所屬大隊' not in df.columns: df['所屬大隊'] = '未提供'
        if '單位' not in df.columns: df['單位'] = '未提供'
        if '性別' not in df.columns: df['性別'] = '未提供'
            
        df = df.dropna(how='all')
        if '姓名' in df.columns:
            df = df.dropna(subset=['姓名'])
        else:
            df['姓名'] = '未具名'
        
        score_cols = [c for c in df.columns if str(c).endswith('_成績')]
        test_metrics = [c.replace('_成績', '') for c in score_cols]
        
        record_cols = [c for c in df.columns if any(x in c for x in ['_最佳', '_次數', '_趟數', '_總秒數', '_成績'])]
        numeric_cols = record_cols + ['年齡', '分數總和']
        
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
                
        if '年齡' in df.columns:
            bins = [20, 30, 40, 50, 70]
            labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
            df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        else:
            df['年齡層'] = '未提供'
            
        if '測驗日期' not in df.columns:
            df['測驗日期'] = '114年下半年'
            
        return df, test_metrics
        
    except Exception as e:
        st.error(f"資料讀取或清理失敗，請檢查。錯誤訊息：{e}")
        return None, []

# --- 讀取資料 ---
df, test_metrics = load_and_clean_data()

record_col_mapping = {
    '立定跳遠': '立定跳遠_最佳',
    '後拋擲遠': '後拋擲遠_最佳',
    '折返跑': '折返跑_趟數',
    '菱形槓硬舉': '菱形槓硬舉_最佳',
    '懸吊屈體': '懸吊屈體_次數',
    '負重行走': '負重行走_最佳',
    '1500公尺跑步': '1500公尺跑步_總秒數'
}

if df is not None and not df.empty and len(test_metrics) > 0:
    all_dates = sorted(df['測驗日期'].dropna().unique(), reverse=True)
    latest_date = all_dates[0] if all_dates else '本次測驗'
    
    score_col_names = [m + '_成績' for m in test_metrics]
    df_tested = df.dropna(subset=score_col_names, how='all')
    
    k1, k2, k3, k4, k5 = st.columns(5)
    latest_tested_df = df_tested[df_tested['測驗日期'] == latest_date]
    
    with k1: st.metric("本次受測人數", f"{latest_tested_df['姓名'].nunique()} 人")
    with k2: st.metric("單項測驗數", f"{len(test_metrics)} 項")
    with k3: st.metric("參測大隊數", f"{latest_tested_df['所屬大隊'].nunique()} 個")
    with k4: st.metric("參測分隊數", f"{latest_tested_df['單位'].nunique()} 個")
    with k5: st.metric("最新測驗日期", f"{latest_date}")

    tab_overview, tab_group, tab_individual, tab_record, tab_alert, tab_leaderboard = st.tabs([
        "📊 戰情總覽", "🔍 交叉分析", "🎯 個人雷達", "📝 紀錄查詢", "🚨 預警與進步榜", "🏆 總分排行榜"
    ])

    # --- Tab 1: 戰情總覽 ---
    with tab_overview:
        st.markdown("##### 🔍 觀測設定")
        oc1, oc2 = st.columns(2)
        with oc1: selected_metric = st.selectbox("請選擇觀測項目：", test_metrics, key='ov_m')
        with oc2: target_brigades = st.multiselect("篩選大隊 (留白則顯示全縣)：", df_tested['所屬大隊'].dropna().unique())
        
        target_score_col = selected_metric + "_成績"
        
        if target_brigades:
            ov_df = latest_tested_df[latest_tested_df['所屬大隊'].isin(target_brigades)]
            trend_df_source = df_tested[df_tested['所屬大隊'].isin(target_brigades)]
        else:
            ov_df = latest_tested_df
            trend_df_source = df_tested

        c1, c2 = st.columns(2)
        with c1:
            if not ov_df.empty:
                avg_df = ov_df.groupby(['所屬大隊', '單位'])[target_score_col].mean().reset_index()
                fig_bar = px.bar(avg_df, x='單位', y=target_score_col, color='所屬大隊', text_auto='.1f', 
                                 title=f"各單位 {selected_metric} 平均得分 ({latest_date})")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("無相應大隊資料。")
            
        with c2:
            if not trend_df_source.empty:
                trend_df = trend_df_source.groupby('測驗日期')[target_score_col].mean().reset_index()
                if len(trend_df) > 1:
                    fig_line = px.line(trend_df, x='測驗日期', y=target_score_col, markers=True, 
                                       title=f"選定範圍之 {selected_metric} 歷次平均得分趨勢")
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    fig_hist = px.histogram(ov_df, x=target_score_col, nbins=10, 
                                            title=f"選定範圍之 {selected_metric} 得分分布 ({latest_date})",
                                            color_discrete_sequence=['#FF4B4B'])
                    fig_hist.update_layout(yaxis_title="人數")
                    st.plotly_chart(fig_hist, use_container_width=True)

    # --- Tab 2: 族群交叉分析 ---
    with tab_group:
        st.subheader("🕵️ 多維度族群交叉篩選")
        f1, f2, f3 = st.columns(3)
        with f1: s_date = st.multiselect("測驗日期", all_dates, default=[latest_date])
        with f2: s_brigade = st.multiselect("所屬大隊", df_tested['所屬大隊'].dropna().unique(), default=df_tested['所屬大隊'].dropna().unique().tolist())
        with f3: s_met = st.selectbox("分析項目", test_metrics, key='gr_m')
        
        f4, f5, f6 = st.columns(3)
        with f4: s_team = st.multiselect("單位", df_tested['單位'].dropna().unique(), default=df_tested['單位'].dropna().unique().tolist())
        with f5: s_gen = st.multiselect("性別", df_tested['性別'].dropna().unique(), default=df_tested['性別'].dropna().unique().tolist())
        with f6: s_age = st.multiselect("年齡層", df_tested['年齡層'].dropna().unique().tolist(), default=df_tested['年齡層'].dropna().unique().tolist())
        
        filtered = df_tested[
            (df_tested['測驗日期'].isin(s_date)) & 
            (df_tested['所屬大隊'].isin(s_brigade)) & 
            (df_tested['單位'].isin(s_team)) & 
            (df_tested['性別'].isin(s_gen)) & 
            (df_tested['年齡層'].isin(s_age))
        ]
        
        if not filtered.empty:
            target_score_col = s_met + "_成績"
            fig_box = px.box(filtered, x="單位", y=target_score_col, color="所屬大隊", points="all", hover_data=['姓名', '測驗日期'])
            fig_box.update_layout(yaxis_title=f"{s_met} 得分")
            st.plotly_chart(fig_box, use_container_width=True)
            st.info(f"📌 此條件下共篩選出 {len(filtered)} 筆有效得分紀錄。")
        else:
            st.warning("⚠️ 找不到符合篩選條件的資料，請放寬限制。")

    # --- Tab 3: 個人追蹤儀表 (雷達圖) ---
    with tab_individual:
        st.subheader("🎯 個人得分 PR 值雷達圖與常模對比")
        sel_c1, sel_c2, sel_c3 = st.columns(3)
        with sel_c1:
            radar_brigades = df['所屬大隊'].dropna().unique()
            radar_brigade = st.selectbox("1️⃣ 選擇大隊", radar_brigades, key='radar_brigade') if len(radar_brigades) > 0 else None
        with sel_c2:
            radar_units = df[df['所屬大隊'] == radar_brigade]['單位'].dropna().unique() if radar_brigade else []
            radar_unit = st.selectbox("2️⃣ 選擇單位", radar_units, key='radar_unit') if len(radar_units) > 0 else None
        with sel_c3:
            radar_names = df[(df['所屬大隊'] == radar_brigade) & (df['單位'] == radar_unit)]['姓名'].dropna().unique() if radar_unit else []
            p_name = st.selectbox("3️⃣ 選擇隊員", radar_names, key='radar_name') if len(radar_names) > 0 else None
            
        cp1, cp2 = st.columns([1, 2])
        if p_name:
            with cp1:
                p_records = df_tested[df_tested['姓名'] == p_name].sort_values(by='測驗日期', ascending=False)
                
                if not p_records.empty:
                    p_latest = p_records.iloc[0]
                    p_age_group = p_latest.get('年齡層', '未提供')
                    
                    st.info(f"姓名： {p_latest.get('姓名')} | 單位： {p_latest.get('所屬大隊')} - {p_latest.get('單位')} | 年齡層： {p_age_group}")
                    
                    total_score = p_latest.get('分數總和', '無資料')
                    if pd.notna(total_score):
                        st.success(f"🏆 本次測驗分數總和： **{int(total_score)}** 分")
                    else:
                        st.success(f"🏆 本次測驗分數總和： 無資料")

                    age_group_df = latest_tested_df[latest_tested_df['年齡層'] == p_age_group]
                    
                    st.write(f"{latest_date} 最新明細 (紀錄 / 分數)：")
                    for m in test_metrics:
                        score_col = m + '_成績'
                        rec_col = record_col_mapping.get(m, m)
                        
                        rec_val = p_latest[rec_col] if rec_col in p_latest and pd.notna(p_latest[rec_col]) else "-"
                        score_val = p_latest[score_col] if pd.notna(p_latest[score_col]) else "-"
                        
                        age_avg = age_group_df[score_col].mean() if not age_group_df.empty else None
                        age_avg_text = f" | 同齡平均: {age_avg:.1f}分" if age_avg and pd.notna(age_avg) else ""
                        
                        st.write(f"- {m}： {rec_val} / 得 {score_val} 分 <span style='color:gray; font-size:14px;'>{age_avg_text}</span>", unsafe_allow_html=True)
                        
            with cp2:
                if not p_records.empty:
                    radar_scores = []
                    valid_metrics = []
                    
                    for m in test_metrics:
                        score_col = m + '_成績'
                        val = p_latest[score_col]
                        if pd.notna(val):
                            latest_all = latest_tested_df[score_col].dropna()
                            if len(latest_all) > 0:
                                pr = (latest_all <= val).mean() * 100
                                radar_scores.append(pr)
                                valid_metrics.append(m)

                    if len(valid_metrics) > 2:
                        radar_df = pd.DataFrame({'項目': valid_metrics, 'PR值 (全縣百分等級)': radar_scores})
                        fig_radar = px.line_polar(radar_df, r='PR值 (全縣百分等級)', theta='項目', line_close=True, range_r=[0, 100])
                        fig_radar.update_traces(fill='toself', line_color='#1E90FF')
                        fig_radar.update_layout(polar=dict(radialaxis=dict(showticklabels=False))) 
                        st.plotly_chart(fig_radar, use_container_width=True)
                    else:
                        st.warning("該員有效成績項目不足，無法繪製雷達圖。")

    # --- Tab 4: 個人紀錄查詢 ---
    with tab_record:
        st.subheader("📝 個人歷次測驗紀錄查詢 (原始數據：次數 / 最佳紀錄 / 秒數)")
        rc1, rc2, rc3 = st.columns(3)
        with rc1: 
            rec_brigades = df['所屬大隊'].dropna().unique()
            rec_brigade = st.selectbox("1️⃣ 選擇大隊", rec_brigades, key='rec_brigade') if len(rec_brigades) > 0 else None
        with rc2: 
            rec_units = df[df['所屬大隊'] == rec_brigade]['單位'].dropna().unique() if rec_brigade else []
            rec_unit = st.selectbox("2️⃣ 選擇單位", rec_units, key='rec_unit') if len(rec_units) > 0 else None
        with rc3:
            rec_names = df[(df['所屬大隊'] == rec_brigade) & (df['單位'] == rec_unit)]['姓名'].dropna().unique() if rec_unit else []
            rec_name = st.selectbox("3️⃣ 選擇隊員", rec_names, key='rec_name') if len(rec_names) > 0 else None
            
        if rec_name:
            p_records_all = df[df['姓名'] == rec_name].sort_values(by='測驗日期', ascending=False)
            
            if not p_records_all.empty:
                display_rec_cols = [record_col_mapping.get(m, m) for m in test_metrics]
                display_cols = ['測驗日期'] + [c for c in display_rec_cols if c in p_records_all.columns]
                
                st.markdown(f"##### 📋 {rec_name} - 歷次「測驗紀錄」總表")
                st.dataframe(p_records_all[display_cols], hide_index=True, use_container_width=True)
                
                st.markdown("##### 📈 單項歷次紀錄趨勢")
                rec_metric_base = st.selectbox("請選擇觀測的測驗項目：", test_metrics, key='rec_metric_sel')
                target_rec_col = record_col_mapping.get(rec_metric_base, rec_metric_base)
                
                if target_rec_col in p_records_all.columns:
                    plot_data = p_records_all.dropna(subset=[target_rec_col]).sort_values(by='測驗日期')
                    
                    if not plot_data.empty:
                        fig_rec = px.line(plot_data, x='測驗日期', y=target_rec_col, markers=True, text=target_rec_col)
                        fig_rec.update_traces(textposition="top center")
                        
                        if '秒' in target_rec_col:
                            fig_rec.update_yaxes(autorange="reversed")
                            fig_rec.update_layout(title=f"{rec_name} - {rec_metric_base} 歷次紀錄 (秒數越少越佳)")
                        else:
                            fig_rec.update_layout(title=f"{rec_name} - {rec_metric_base} 歷次紀錄 (數值越多越佳)")
                        st.plotly_chart(fig_rec, use_container_width=True)
                    else:
                        st.info(f"該員尚無 {rec_metric_base} 的測驗紀錄。")
                else:
                    st.info("資料表中無此紀錄欄位。")

    # --- Tab 5: 預警與進步榜 ---
    with tab_alert:
        ca1, ca2, ca3 = st.columns(3)
        
        with ca1:
            st.markdown("##### ❌ 自訂未達標監控")
            fail_m = st.selectbox("監控達標項目 (以分數為準)：", test_metrics, key='al_f1')
            fail_score_col = fail_m + '_成績'
            fail_val = st.number_input("最低及格標準：", value=60)
            
            fail_list = latest_tested_df[latest_tested_df[fail_score_col] < fail_val]
            if not fail_list.empty:
                st.dataframe(fail_list[['所屬大隊', '單位', '姓名', fail_score_col]].style.map(
                    lambda x: 'background-color: #ffcccc; color: black;' if isinstance(x, (int, float)) and x < fail_val else '', subset=[fail_score_col]
                ), hide_index=True, use_container_width=True)
            else:
                st.success("🎉 本次測驗全員通過！")

        with ca2:
            st.markdown("##### 🔥 退步輔導名單")
            reg_m = st.selectbox("監控退步項目 (以分數為準)：", test_metrics, key='al_r1')
            reg_score_col = reg_m + "_成績"
            reg_val = st.number_input("容許退步空間 (減少幾分)：", value=10)
            
            if len(all_dates) > 1:
                d_now = latest_tested_df[['所屬大隊', '單位', '姓名', reg_score_col]]
                d_old = df_tested[df_tested['測驗日期']==all_dates[1]][['姓名', reg_score_col]]
                merged = pd.merge(d_now, d_old, on='姓名', suffixes=('_今', '_昨')).dropna()
                
                merged['退步幅度'] = merged[f'{reg_score_col}_昨'] - merged[f'{reg_score_col}_今']
                regression = merged[merged['退步幅度'] > reg_val].sort_values(by='退步幅度', ascending=False)
                
                if not regression.empty:
                    st.dataframe(regression[['所屬大隊', '單位', '姓名', '退步幅度']], hide_index=True, use_container_width=True)
                else:
                    st.success("🎉 無人觸發退步警示！")
            else:
                st.info("資料不足兩次測驗，無法比對。")

        with ca3:
            st.markdown("##### 🏆 最佳進步榜")
            prog_m = st.selectbox("觀察進步項目 (以分數為準)：", test_metrics, key='al_p1')
            prog_score_col = prog_m + "_成績"
            prog_val = st.number_input("顯示進步超過幾分：", value=5)
            
            if len(all_dates) > 1:
                d_now = latest_tested_df[['所屬大隊', '單位', '姓名', prog_score_col]]
                d_old = df_tested[df_tested['測驗日期']==all_dates[1]][['姓名', prog_score_col]]
                merged = pd.merge(d_now, d_old, on='姓名', suffixes=('_今', '_昨')).dropna()
                
                merged['進步幅度'] = merged[f'{prog_score_col}_今'] - merged[f'{prog_score_col}_昨']
                progress = merged[merged['進步幅度'] >= prog_val].sort_values(by='進步幅度', ascending=False)
                
                if not progress.empty:
                    st.dataframe(progress[['所屬大隊', '單位', '姓名', '進步幅度']].style.map(
                        lambda x: 'background-color: #ccffcc; color: black;' if isinstance(x, (int, float)) and x >= prog_val else '', subset=['進步幅度']
                    ), hide_index=True, use_container_width=True)
                else:
                    st.info("目前無人達到設定的進步門檻。")
            else:
                st.info("資料不足兩次測驗，無法比對。")

    # --- Tab 6: 總分排行榜 ---
    with tab_leaderboard:
        st.subheader("🏆 單位與個人分數總和排行榜")
        
        if '分數總和' in latest_tested_df.columns:
            lb1, lb2 = st.columns(2)
            
            with lb1:
                st.markdown(f"##### 🥇 全縣個人總分 Top 15 ({latest_date})")
                top_individuals = latest_tested_df.dropna(subset=['分數總和']).sort_values(by='分數總和', ascending=False).head(15)
                
                if not top_individuals.empty:
                    top_individuals.insert(0, '名次', range(1, len(top_individuals) + 1))
                    top_individuals['分數總和'] = top_individuals['分數總和'].astype(int)
                    
                    # 🌟 這裡處理並加入年齡欄位
                    if '年齡' in top_individuals.columns:
                        # 轉成 Int64 可避免 NaN 導致的小數點問題
                        top_individuals['年齡'] = top_individuals['年齡'].astype('Int64')
                        display_cols = ['名次', '所屬大隊', '單位', '姓名', '年齡', '分數總和']
                    else:
                        display_cols = ['名次', '所屬大隊', '單位', '姓名', '分數總和']
                        
                    st.dataframe(top_individuals[display_cols], hide_index=True, use_container_width=True)
                else:
                    st.info("目前尚無分數總和資料。")
                    
            with lb2:
                st.markdown(f"##### 🏢 各單位平均總分排行榜 ({latest_date})")
                unit_avg_total = latest_tested_df.dropna(subset=['分數總和']).groupby(['所屬大隊', '單位'])['分數總和'].mean().reset_index()
                unit_avg_total = unit_avg_total.sort_values(by='分數總和', ascending=False)
                
                if not unit_avg_total.empty:
                    unit_avg_total.insert(0, '名次', range(1, len(unit_avg_total) + 1))
                    unit_avg_total['分數總和'] = unit_avg_total['分數總和'].round(1)
                    st.dataframe(unit_avg_total[['名次', '所屬大隊', '單位', '分數總和']], hide_index=True, use_container_width=True)
                else:
                    st.info("目前尚無單位平均資料。")
        else:
            st.warning("⚠️ 資料表中找不到「分數總和」欄位，請確認 Google 試算表格式。")

else:
    st.info("等待讀取資料庫，或資料格式不符...")
