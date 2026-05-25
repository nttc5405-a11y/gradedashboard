import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="台東縣消防局 - 體技能儀表板 4.0", page_icon="🚒", layout="wide")

# --- 進階樣式 ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF4B4B; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #f8f9fa; padding: 10px; border-radius: 12px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 16px; background-color: #ffffff; border-radius: 8px; padding: 0 20px; color: #555555; border: 1px solid #e0e0e0; transition: all 0.3s ease; }
    .stTabs [data-baseweb="tab"]:hover { background-color: #ffcaea; color: #FF4B4B; border-color: #FF4B4B; }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; color: #ffffff !important; border-color: #FF4B4B !important; box-shadow: 0 4px 6px rgba(255, 75, 75, 0.3); }
    .stTabs [data-baseweb="tab-highlight"] { background-color: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚒 消防局體技能儀表板 v4.0")

# 加入手動更新按鈕
if st.sidebar.button("🔄 強制更新資料庫"):
    st.cache_data.clear()
    st.rerun()

# 延長快取至 10 分鐘，避免頻繁請求 Google Sheets
@st.cache_data(ttl=600)
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

            # ✅ 修正點：移除了 '成績', '總秒數', '趟數', '次數', '最佳'，讓它們進入 elif 合併
            if any(keyword in s for keyword in ['姓名', '大隊', '分隊', '單位', '性別', '年齡', '測驗', '日期', '分數總和']):
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

        # 修正大隊重命名邏輯，避免重複賦值
        rename_map = {}
        has_brigade = False
        for c in df.columns:
            c_str = str(c)
            if c_str in ['消防局大隊', '大隊', '消防大隊', '所屬大隊'] or (('大隊' in c_str) and '_' not in c_str):
                if not has_brigade:
                    rename_map[c] = '消防局大隊'
                    has_brigade = True
            if '分隊' in c_str and '_' not in c_str and c_str != '分隊':
                rename_map[c] = '分隊'
                
        df = df.rename(columns=rename_map)

        if '消防局大隊' not in df.columns: df['消防局大隊'] = '未知大隊'
        if '分隊' not in df.columns: df['分隊'] = '未知分隊'
        if '性別' not in df.columns: df['性別'] = '未知性別'

        df = df.dropna(how='all')
        if '姓名' in df.columns:
            df = df.dropna(subset=['姓名'])
        else:
            df['姓名'] = '未知姓名'

        score_cols = [c for c in df.columns if str(c).endswith('_成績')]
        test_metrics = [c.replace('_成績', '') for c in score_cols]

        record_cols = [c for c in df.columns if any(x in c for x in ['_最佳', '_趟數', '_次數', '_總秒數', '_成績'])]
        numeric_cols = record_cols + ['年齡', '分數總和']

        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')

        if '年齡' in df.columns:
            bins = [20, 30, 40, 50, 70]
            labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
            df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        else:
            df['年齡層'] = '未知年齡'

        # 確保有測驗日期欄位
        date_col = next((c for c in df.columns if '測驗' in c or '日期' in c), None)
        if date_col:
            df = df.rename(columns={date_col: '測驗日期'})
        if '測驗日期' not in df.columns:
            df['測驗日期'] = '114年下半年'

        # 特殊狀態標記
        special_keywords = ['病號', '支援訓中', '公傷', '請假']
        df['特殊狀態'] = ''
        for c in df.columns:
            if c not in ['姓名', '消防局大隊', '分隊', '性別', '年齡', '年齡層', '測驗日期']:
                for kw in special_keywords:
                    mask = df[c].astype(str).str.contains(kw, na=False)
                    df.loc[mask & (df['特殊狀態'] == ''), '特殊狀態'] = kw

        return df, test_metrics

    except Exception as e:
        st.error(f"載入資料失敗，請確認網路狀態。錯誤訊息：{e}")
        return None, []

# --- 載入資料 ---
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
    latest_date = all_dates[0] if all_dates else '無測驗日期'

    score_col_names = [m + '_成績' for m in test_metrics]
    df_tested = df.dropna(subset=score_col_names, how='all')
    latest_tested_df = df_tested[df_tested['測驗日期'] == latest_date]

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("最新測驗大隊數", f"{latest_tested_df['消防局大隊'].nunique()} 隊")
    with k2: st.metric("測驗項目數", f"{len(test_metrics)} 項")
    with k3: st.metric("最新測驗人數", f"{len(latest_tested_df)} 人")
    with k4: st.metric("分隊數", f"{latest_tested_df['分隊'].nunique()} 隊")
    with k5: st.metric("最新測驗日期", f"{latest_date}")

    # 特殊狀態人員統計
    special_df = df[df['特殊狀態'] != '']
    if not special_df.empty:
        st.warning(f"⚠️ 本次資料中有 {len(special_df)} 名特殊狀態人員（病號/支援訓中等），成績可能為空。")

    tab_overview, tab_group, tab_individual, tab_record, tab_alert, tab_leaderboard, tab_planning, tab_stats = st.tabs([
        "📊 總覽概況", "📌 分組比較", "🏷️ 個人體能", "📝 個人紀錄", "🚨 預警系統", "🏆 排行榜", "📋 訓練規劃", "🔬 深度分析"
    ])

    # ==========================================
    # ===== 共用 UI 元件 (DRY 原則) =====
    # ==========================================
    def render_personnel_selector(prefix_key):
        c1, c2, c3 = st.columns(3)
        with c1:
            brigades = df['消防局大隊'].dropna().unique()
            sel_brigade = st.selectbox("1️⃣ 選擇大隊", brigades, key=f'{prefix_key}_b') if len(brigades) > 0 else None
        with c2:
            units = df[df['消防局大隊'] == sel_brigade]['分隊'].dropna().unique() if sel_brigade else []
            sel_unit = st.selectbox("2️⃣ 選擇分隊", units, key=f'{prefix_key}_u') if len(units) > 0 else None
        with c3:
            names = df[(df['消防局大隊'] == sel_brigade) & (df['分隊'] == sel_unit)]['姓名'].dropna().unique() if sel_unit else []
            sel_name = st.selectbox("3️⃣ 選擇姓名", names, key=f'{prefix_key}_n') if len(names) > 0 else None
        return sel_name


    # ===== Tab 1: 總覽概況 =====
    with tab_overview:
        st.markdown("##### 📌 項目篩選")
        oc1, oc2 = st.columns(2)
        with oc1: selected_metric = st.selectbox("選擇比較的測驗項目：", test_metrics, key='ov_m')
        with oc2: target_brigades = st.multiselect("篩選大隊（空白顯示全部）：", df_tested['消防局大隊'].dropna().unique())

        target_score_col = selected_metric + "_成績"

        if target_brigades:
            ov_df = latest_tested_df[latest_tested_df['消防局大隊'].isin(target_brigades)]
            trend_df_source = df_tested[df_tested['消防局大隊'].isin(target_brigades)]
        else:
            ov_df = latest_tested_df
            trend_df_source = df_tested

        c1, c2 = st.columns(2)
        with c1:
            if not ov_df.empty:
                avg_df = ov_df.groupby(['消防局大隊', '分隊'])[target_score_col].mean().reset_index()
                fig_bar = px.bar(avg_df, x='分隊', y=target_score_col, color='消防局大隊', text_auto='.1f',
                                 title=f"分隊別 {selected_metric} 平均成績 ({latest_date})")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("無符合大隊的資料。")

        with c2:
            if not trend_df_source.empty:
                trend_df = trend_df_source.groupby('測驗日期')[target_score_col].mean().reset_index()
                if len(trend_df) > 1:
                    fig_line = px.line(trend_df, x='測驗日期', y=target_score_col, markers=True,
                                       title=f"歷年成績 {selected_metric} 趨勢變化")
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    fig_hist = px.histogram(ov_df, x=target_score_col, nbins=10,
                                            title=f"{selected_metric} 分布 ({latest_date})",
                                            color_discrete_sequence=['#FF4B4B'])
                    fig_hist.update_layout(yaxis_title="人數")
                    st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🔥 大隊 × 測驗項目平均成績熱圖")
        st.caption("顏色越紅代表該大隊在該項目的平均成績越低，可快速識別弱點。")
        heatmap_data = []
        brigades_list = latest_tested_df['消防局大隊'].dropna().unique()
        for brigade in brigades_list:
            row = {'大隊': brigade}
            for m in test_metrics:
                sc = m + '_成績'
                if sc in latest_tested_df.columns:
                    vals = latest_tested_df[latest_tested_df['消防局大隊'] == brigade][sc].dropna()
                    row[m] = round(vals.mean(), 1) if len(vals) > 0 else None
            heatmap_data.append(row)

        if heatmap_data:
            heatmap_df = pd.DataFrame(heatmap_data).set_index('大隊')
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=heatmap_df.values,
                x=heatmap_df.columns.tolist(),
                y=heatmap_df.index.tolist(),
                colorscale='RdYlGn',
                text=heatmap_df.values,
                texttemplate='%{text}',
                textfont={"size": 13},
                hoverongaps=False,
                zmin=1, zmax=20
            ))
            fig_heatmap.update_layout(
                title=f"大隊 × 項目平均成績熱圖（{latest_date}）",
                xaxis_title="測驗項目",
                yaxis_title="大隊",
                height=max(300, len(brigades_list) * 60 + 100)
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

        if not special_df.empty:
            with st.expander(f"🏥 特殊狀態人員清單（共 {len(special_df)} 人）"):
                show_cols = ['消防局大隊', '分隊', '姓名', '特殊狀態']
                show_cols = [c for c in show_cols if c in special_df.columns]
                st.dataframe(special_df[show_cols], hide_index=True, use_container_width=True)

    # ===== Tab 2: 分組比較 + 描述性統計 =====
    with tab_group:
        st.subheader("🖥️ 篩選條件與盒鬚圖比較")
        f1, f2, f3 = st.columns(3)
        with f1: s_date = st.multiselect("測驗日期", all_dates, default=[latest_date])
        with f2: s_brigade = st.multiselect("消防局大隊", df_tested['消防局大隊'].dropna().unique(), default=df_tested['消防局大隊'].dropna().unique().tolist())
        with f3: s_met = st.selectbox("項目選擇", test_metrics, key='gr_m')

        f4, f5, f6 = st.columns(3)
        with f4: s_team = st.multiselect("分隊", df_tested['分隊'].dropna().unique(), default=df_tested['分隊'].dropna().unique().tolist())
        with f5: s_gen = st.multiselect("性別", df_tested['性別'].dropna().unique(), default=df_tested['性別'].dropna().unique().tolist())
        with f6: s_age = st.multiselect("年齡層", df_tested['年齡層'].dropna().unique().tolist(), default=df_tested['年齡層'].dropna().unique().tolist())

        filtered = df_tested[
            (df_tested['測驗日期'].isin(s_date)) &
            (df_tested['消防局大隊'].isin(s_brigade)) &
            (df_tested['分隊'].isin(s_team)) &
            (df_tested['性別'].isin(s_gen)) &
            (df_tested['年齡層'].isin(s_age))
        ]

        if not filtered.empty:
            target_score_col = s_met + "_成績"
            fig_box = px.box(filtered, x="分隊", y=target_score_col, color="消防局大隊", points="all", hover_data=['姓名', '測驗日期'])
            fig_box.update_layout(yaxis_title=f"{s_met} 成績")
            st.plotly_chart(fig_box, use_container_width=True)
            st.info(f"📌 符合條件共有 {len(filtered)} 筆有效成績資料。")

            csv_data = filtered.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="⬇️ 下載篩選資料 CSV",
                data=csv_data.encode('utf-8-sig'),
                file_name=f"體技能篩選資料_{s_met}_{latest_date}.csv",
                mime="text/csv"
            )

            st.markdown("---")
            st.markdown("#### 📊 描述性統計分析")
            desc_tab1, desc_tab2 = st.tabs(["📈 整體描述統計", "📋 分組統計表"])

            with desc_tab1:
                all_score_cols = [m + '_成績' for m in test_metrics if m + '_成績' in filtered.columns]
                if all_score_cols:
                    desc_df = filtered[all_score_cols].describe().T
                    desc_df.index = [c.replace('_成績', '') for c in desc_df.index]
                    desc_df.columns = ['筆數', '平均', '標準差', '最低', '25%', '中位數', '75%', '最高']
                    desc_df = desc_df.round(2)
                    st.dataframe(desc_df, use_container_width=True)

                    std_data = desc_df[['標準差']].reset_index()
                    std_data.columns = ['項目', '標準差']
                    fig_std = px.bar(std_data, x='項目', y='標準差', text='標準差',
                                     title="各項目成績標準差（成績波動性比較）",
                                     color='標準差', color_continuous_scale=['#28a745', '#ffc107', '#dc3545'])
                    fig_std.update_traces(textposition='outside')
                    fig_std.update_layout(coloraxis_showscale=False, xaxis_title="", yaxis_title="標準差")
                    st.plotly_chart(fig_std, use_container_width=True)

            with desc_tab2:
                group_by_col = st.selectbox("分組依據", ['消防局大隊', '分隊', '性別', '年齡層'], key='desc_group')
                if target_score_col in filtered.columns:
                    grp_desc = filtered.groupby(group_by_col)[target_score_col].agg(
                        人數='count', 平均='mean', 標準差='std', 最低='min', 中位數='median', 最高='max'
                    ).round(2).reset_index()
                    st.dataframe(grp_desc, hide_index=True, use_container_width=True)

                    fig_grp = px.bar(grp_desc, x=group_by_col, y='平均', error_y='標準差', text='平均',
                                     title=f"{s_met} 各{group_by_col}平均±標準差",
                                     color='平均', color_continuous_scale=['#dc3545', '#ffc107', '#28a745'])
                    fig_grp.update_traces(textposition='outside')
                    fig_grp.update_layout(coloraxis_showscale=False, xaxis_title="", yaxis_title="平均成績")
                    st.plotly_chart(fig_grp, use_container_width=True)
        else:
            st.warning("⚠️ 無符合條件的資料，請調整篩選條件。")

    # ===== Tab 3: 個人體能 =====
    with tab_individual:
        st.subheader("🏷️ 個人體能 PR 值雷達圖（同性別+年齡層比較）")
        p_name = render_personnel_selector('radar')

        cp1, cp2 = st.columns([1, 2])
        if p_name:
            with cp1:
                p_records = df_tested[df_tested['姓名'] == p_name].sort_values(by='測驗日期', ascending=False)
                if not p_records.empty:
                    p_latest = p_records.iloc[0]
                    p_age_group = p_latest.get('年齡層', '未知')
                    p_gender = p_latest.get('性別', '未知')

                    st.info(f"姓名：{p_latest.get('姓名')} | {p_latest.get('消防局大隊')} - {p_latest.get('分隊')} | {p_age_group} | {p_gender}")

                    total_score = p_latest.get('分數總和', '計算中')
                    if pd.notna(total_score):
                        st.success(f"🏅 最新測驗總成績：{int(total_score)} 分")

                    same_group_df = latest_tested_df[
                        (latest_tested_df['性別'] == p_gender) &
                        (latest_tested_df['年齡層'] == p_age_group)
                    ]
                    group_label = f"（{p_gender} / {p_age_group} 同組，共 {len(same_group_df)} 人）"

                    st.write(f"{latest_date} 各項成績 {group_label}：")
                    for m in test_metrics:
                        score_col = m + '_成績'
                        rec_col = record_col_mapping.get(m, m)

                        rec_val = p_latest[rec_col] if rec_col in p_latest and pd.notna(p_latest[rec_col]) else "-"
                        score_val = p_latest[score_col] if pd.notna(p_latest[score_col]) else "-"

                        age_avg = same_group_df[score_col].mean() if not same_group_df.empty else None
                        age_avg_text = f" | 同組均值：{age_avg:.1f}分" if age_avg and pd.notna(age_avg) else ""

                        st.write(f"- {m}：{rec_val} / 成績 {score_val} 分 <span style='color:gray; font-size:14px;'>{age_avg_text}</span>", unsafe_allow_html=True)

            with cp2:
                if not p_records.empty:
                    radar_scores = []
                    valid_metrics = []

                    for m in test_metrics:
                        score_col = m + '_成績'
                        val = p_latest[score_col]
                        if pd.notna(val):
                            same_group_vals = same_group_df[score_col].dropna()
                            if len(same_group_vals) > 0:
                                pr = (same_group_vals <= val).mean() * 100
                                radar_scores.append(pr)
                                valid_metrics.append(m)

                    if len(valid_metrics) > 2:
                        radar_df = pd.DataFrame({'項目': valid_metrics, 'PR值（同組百分位）': radar_scores})
                        fig_radar = px.line_polar(radar_df, r='PR值（同組百分位）', theta='項目', line_close=True, range_r=[0, 100])
                        fig_radar.update_traces(fill='toself', line_color='#1E90FF')
                        fig_radar.update_layout(
                            polar=dict(radialaxis=dict(showticklabels=False)),
                            title=f"{p_name} 各項目同組百分位雷達圖"
                        )
                        st.plotly_chart(fig_radar, use_container_width=True)
                        st.caption(f"⚠️ PR值為在相同性別+年齡層（{p_gender}/{p_age_group}，共{len(same_group_df)}人）中的百分位，100=該組最佳。")
                    else:
                        st.warning("該員有效成績項目不足，無法產生雷達圖。")

    # ===== Tab 4: 個人紀錄 =====
    with tab_record:
        st.subheader("📝 個人歷次測驗紀錄（原始成績 / 最佳成績 / 趟數）")
        rec_name = render_personnel_selector('rec')

        if rec_name:
            p_records_all = df[df['姓名'] == rec_name].sort_values(by='測驗日期', ascending=False)

            if not p_records_all.empty:
                display_rec_cols = [record_col_mapping.get(m, m) for m in test_metrics]
                display_cols = ['測驗日期'] + [c for c in display_rec_cols if c in p_records_all.columns]

                st.markdown(f"##### 📋 {rec_name} - 歷次測驗紀錄")
                st.dataframe(p_records_all[display_cols], hide_index=True, use_container_width=True)

                st.markdown("---")
                st.markdown("##### 📊 歷次成績趨勢")
                rec_metric_base = st.selectbox("選擇查看歷次的測驗項目：", test_metrics, key='rec_metric_sel')
                target_rec_col = record_col_mapping.get(rec_metric_base, rec_metric_base)

                attempt_cols = [c for c in p_records_all.columns if rec_metric_base in c and c != target_rec_col and c != rec_metric_base + '_成績']
                if attempt_cols and not p_records_all.empty:
                    st.markdown("各試次成績（最新一次測驗）：")
                    latest_attempt_row = p_records_all.iloc[0]
                    attempt_vals = []
                    for ac in attempt_cols:
                        v = latest_attempt_row.get(ac)
                        if pd.notna(v):
                            try:
                                attempt_vals.append({'試次': ac, '成績': float(v)})
                            except:
                                pass
                    if attempt_vals:
                        att_df = pd.DataFrame(attempt_vals)
                        fig_att = px.bar(att_df, x='試次', y='成績', text='成績',
                                         title=f"{rec_name} - {rec_metric_base} 各試次成績",
                                         color_discrete_sequence=['#1E90FF'])
                        if '秒' in target_rec_col:
                            fig_att.update_yaxes(autorange="reversed")
                        fig_att.update_traces(textposition='outside')
                        st.plotly_chart(fig_att, use_container_width=True)

                if target_rec_col in p_records_all.columns:
                    plot_data = p_records_all.dropna(subset=[target_rec_col]).sort_values(by='測驗日期')
                    if not plot_data.empty:
                        fig_rec = px.line(plot_data, x='測驗日期', y=target_rec_col, markers=True, text=target_rec_col)
                        fig_rec.update_traces(textposition="top center")
                        if '秒' in target_rec_col:
                            fig_rec.update_yaxes(autorange="reversed")
                            fig_rec.update_layout(title=f"{rec_name} - {rec_metric_base} 歷次紀錄（秒數越低越好）")
                        else:
                            fig_rec.update_layout(title=f"{rec_name} - {rec_metric_base} 歷次紀錄（數值越高越好）")
                        st.plotly_chart(fig_rec, use_container_width=True)
                    else:
                        st.info(f"該員沒有 {rec_metric_base} 的測驗紀錄。")
                else:
                    st.info("找不到對應的成績紀錄欄位。")

    # ===== Tab 5: 預警系統 =====
    with tab_alert:
        ca1, ca2, ca3 = st.columns(3)

        with ca1:
            st.markdown("##### ❌ 單項成績落後預警")
            fail_m = st.selectbox("落後預警項目（低於閾值）：", test_metrics, key='al_f1')
            fail_score_col = fail_m + '_成績'
            fail_val = st.number_input("最低及格成績閾值：", value=60)

            fail_list = latest_tested_df[latest_tested_df[fail_score_col] < fail_val]
            if not fail_list.empty:
                st.dataframe(fail_list[['消防局大隊', '分隊', '姓名', fail_score_col]].style.map(
                    lambda x: 'background-color: #ffcccc; color: black;' if isinstance(x, (int, float)) and x < fail_val else '', subset=[fail_score_col]
                ), hide_index=True, use_container_width=True)
            else:
                st.success("🎉 最新測驗全員通過！")

        with ca2:
            st.markdown("##### 📉 進步幅度退步預警")
            reg_m = st.selectbox("退步預警項目：", test_metrics, key='al_r1')
            reg_score_col = reg_m + "_成績"
            reg_val = st.number_input("連續退步幅度閾值（減少超過）：", value=10)

            if len(all_dates) > 1:
                d_now = latest_tested_df[['消防局大隊', '分隊', '姓名', reg_score_col]]
                d_old = df_tested[df_tested['測驗日期']==all_dates[1]][['姓名', reg_score_col]]
                merged = pd.merge(d_now, d_old, on='姓名', suffixes=('_新', '_舊')).dropna()

                merged['退步幅度'] = merged[f'{reg_score_col}_舊'] - merged[f'{reg_score_col}_新']
                regression = merged[merged['退步幅度'] > reg_val].sort_values(by='退步幅度', ascending=False)

                if not regression.empty:
                    st.dataframe(regression[['消防局大隊', '分隊', '姓名', '退步幅度']], hide_index=True, use_container_width=True)
                else:
                    st.success("🎉 沒有達到顯著退步標準！")
            else:
                st.info("目前只有一期測驗資料，無法進行退步比較。")

        with ca3:
            st.markdown("##### 🏅 進步排行")
            prog_m = st.selectbox("進步排行項目：", test_metrics, key='al_p1')
            prog_score_col = prog_m + "_成績"
            prog_val = st.number_input("進步幅度閾值：", value=5)

            if len(all_dates) > 1:
                d_now = latest_tested_df[['消防局大隊', '分隊', '姓名', prog_score_col]]
                d_old = df_tested[df_tested['測驗日期']==all_dates[1]][['姓名', prog_score_col]]
                merged = pd.merge(d_now, d_old, on='姓名', suffixes=('_新', '_舊')).dropna()

                merged['進步幅度'] = merged[f'{prog_score_col}_新'] - merged[f'{prog_score_col}_舊']
                progress = merged[merged['進步幅度'] >= prog_val].sort_values(by='進步幅度', ascending=False)

                if not progress.empty:
                    st.dataframe(progress[['消防局大隊', '分隊', '姓名', '進步幅度']].style.map(
                        lambda x: 'background-color: #ccffcc; color: black;' if isinstance(x, (int, float)) and x >= prog_val else '', subset=['進步幅度']
                    ), hide_index=True, use_container_width=True)
                else:
                    st.info("目前沒有到達進步標準的成員。")
            else:
                st.info("目前只有一期測驗資料，無法進行進步比較。")

    # ===== Tab 6: 排行榜 =====
    with tab_leaderboard:
        st.subheader("🏆 分隊別個人總成績排行榜")

        if '分數總和' in latest_tested_df.columns:
            lb1, lb2 = st.columns(2)

            with lb1:
                st.markdown(f"##### 🥇 全局個人排行 Top 15 ({latest_date})")
                top_individuals = latest_tested_df.dropna(subset=['分數總和']).sort_values(by='分數總和', ascending=False).head(15).copy()

                if not top_individuals.empty:
                    top_individuals.insert(0, '名次', range(1, len(top_individuals) + 1))
                    top_individuals['分數總和'] = top_individuals['分數總和'].astype(int)
                    if '年齡' in top_individuals.columns:
                        top_individuals['年齡'] = top_individuals['年齡'].astype('Int64')
                        display_cols = ['名次', '消防局大隊', '分隊', '姓名', '年齡', '分數總和']
                    else:
                        display_cols = ['名次', '消防局大隊', '分隊', '姓名', '分數總和']
                    st.dataframe(top_individuals[display_cols], hide_index=True, use_container_width=True)
                else:
                    st.info("未找到分數總和資料。")

            with lb2:
                st.markdown(f"##### 🎯 分隊平均總成績排行榜 ({latest_date})")
                unit_avg_total = latest_tested_df.dropna(subset=['分數總和']).groupby(['消防局大隊', '分隊'])['分數總和'].mean().reset_index()
                unit_avg_total = unit_avg_total.sort_values(by='分數總和', ascending=False).copy()

                if not unit_avg_total.empty:
                    unit_avg_total.insert(0, '名次', range(1, len(unit_avg_total) + 1))
                    unit_avg_total['分數總和'] = unit_avg_total['分數總和'].round(1)
                    st.dataframe(unit_avg_total[['名次', '消防局大隊', '分隊', '分數總和']], hide_index=True, use_container_width=True)
                else:
                    st.info("未找到分隊平均資料。")
        else:
            st.warning("⚠️ 找不到「分數總和」欄位，請確認 Google Sheets 設定。")

    # ===== Tab 7: 訓練規劃 =====
    with tab_planning:
        st.subheader("📋 訓練規劃與體能現況分析報告")
        st.caption(f"以下分析基於 {latest_date} 測驗資料，共 {latest_tested_df['姓名'].nunique()} 名人員")

        st.markdown("---")
        st.markdown("#### 一、整體體能現況")
        if '分數總和' in latest_tested_df.columns and len(test_metrics) > 0:
            scored_df = latest_tested_df.dropna(subset=['分數總和']).copy()
            n_tests = len(test_metrics)
            scored_df['平均單項成績'] = (scored_df['分數總和'] / n_tests).round(1)

            def classify_risk(score):
                if score >= 90: return '✅ 優秀 (≥90分)'
                elif score >= 70: return '⚠️ 警戒 (70-89分)'
                elif score >= 50: return '🟠 加強 (50-69分)'
                else: return '🔴 高風險 (<50分)'

            scored_df['風險等級'] = scored_df['分數總和'].apply(classify_risk)
            risk_counts = scored_df['風險等級'].value_counts().reset_index()
            risk_counts.columns = ['等級', '人數']

            rc1, rc2, rc3, rc4 = st.columns(4)
            level_config = {
                '✅ 優秀 (≥90分)': rc1,
                '⚠️ 警戒 (70-89分)': rc2,
                '🟠 加強 (50-69分)': rc3,
                '🔴 高風險 (<50分)': rc4,
            }
            for level, col in level_config.items():
                count = int(risk_counts[risk_counts['等級'] == level]['人數'].sum()) if level in risk_counts['等級'].values else 0
                pct = count / len(scored_df) * 100 if len(scored_df) > 0 else 0
                with col:
                    st.metric(level, f"{count} 人", f"{pct:.1f}%")

            risk_order = ['🔴 高風險 (<50分)', '🟠 加強 (50-69分)', '⚠️ 警戒 (70-89分)', '✅ 優秀 (≥90分)']
            risk_color_map = {
                '✅ 優秀 (≥90分)': '#28a745',
                '⚠️ 警戒 (70-89分)': '#ffc107',
                '🟠 加強 (50-69分)': '#fd7e14',
                '🔴 高風險 (<50分)': '#dc3545',
            }
            fig_risk = px.bar(
                risk_counts, x='等級', y='人數', text='人數',
                color='等級', color_discrete_map=risk_color_map,
                category_orders={'等級': risk_order},
                title="全局風險等級分布（以總成績計）"
            )
            fig_risk.update_traces(textposition='outside')
            fig_risk.update_layout(showlegend=False, xaxis_title="", yaxis_title="人數")
            st.plotly_chart(fig_risk, use_container_width=True)

            high_risk_list = scored_df[scored_df['風險等級'] == '🔴 高風險 (<50分)']
            if not high_risk_list.empty:
                with st.expander(f"🔴 高風險人員名單（共 {len(high_risk_list)} 人）─ 點擊展開"):
                    display_risk_cols = ['消防局大隊', '分隊', '姓名', '年齡', '平均單項成績', '分數總和']
                    display_risk_cols = [c for c in display_risk_cols if c in high_risk_list.columns]
                    st.dataframe(high_risk_list[display_risk_cols].sort_values('平均單項成績'), hide_index=True, use_container_width=True)
        else:
            st.warning("⚠️ 無分數總和資料，無法計算風險等級。")

        st.markdown("---")
        st.markdown("#### 二、項目別全局弱點分析")
        score_avgs = []
        for m in test_metrics:
            sc = m + '_成績'
            if sc in latest_tested_df.columns:
                vals = latest_tested_df[sc].dropna()
                if len(vals) > 0:
                    score_avgs.append({
                        '測驗項目': m,
                        '全局平均成績': round(vals.mean(), 1),
                        '低於60分人數': int((vals < 60).sum()),
                        '低於60分比率': round((vals < 60).mean() * 100, 1),
                    })

        if score_avgs:
            avg_score_df = pd.DataFrame(score_avgs).sort_values(by='全局平均成績')

            diag1, diag2 = st.columns([3, 2])
            with diag1:
                fig_avg = px.bar(
                    avg_score_df, x='測驗項目', y='全局平均成績', text='全局平均成績',
                    title="項目別全局平均成績（由低到高）",
                    color='全局平均成績',
                    color_continuous_scale=['#dc3545', '#ffc107', '#28a745']
                )
                fig_avg.update_traces(textposition='outside')
                fig_avg.update_layout(coloraxis_showscale=False, xaxis_title="", yaxis_title="平均成績")
                st.plotly_chart(fig_avg, use_container_width=True)

            with diag2:
                fig_fail = px.bar(
                    avg_score_df.sort_values('低於60分比率', ascending=False),
                    x='測驗項目', y='低於60分比率', text='低於60分比率',
                    title="項目別低於60分比率（%）",
                    color='低於60分比率',
                    color_continuous_scale=['#28a745', '#ffc107', '#dc3545']
                )
                fig_fail.update_traces(texttemplate='%{text}%', textposition='outside')
                fig_fail.update_layout(coloraxis_showscale=False, xaxis_title="", yaxis_title="比率 (%)")
                st.plotly_chart(fig_fail, use_container_width=True)

            weakest = avg_score_df.iloc[0]['測驗項目']
            weakest_score = avg_score_df.iloc[0]['全局平均成績']
            weakest_fail_rate = avg_score_df.iloc[0]['低於60分比率']
            st.error(f"⚠️ 最弱項目：{weakest}（平均 {weakest_score} 分，{weakest_fail_rate}% 人員低於60分）─ 建議加強專項訓練！")

        st.markdown("---")
        st.markdown("#### 三、年齡層訓練建議")
        age1, age2 = st.columns(2)
        with age1:
            if '年齡層' in latest_tested_df.columns and '分數總和' in latest_tested_df.columns:
                age_df = latest_tested_df.dropna(subset=['年齡層', '分數總和'])
                fig_age_box = px.box(
                    age_df, x='年齡層', y='分數總和', color='年齡層',
                    points='all', hover_data=['姓名', '分隊'],
                    title="年齡層別總成績分布",
                    category_orders={'年齡層': ['20-29歲', '30-39歲', '40-49歲', '50歲以上']}
                )
                fig_age_box.update_layout(showlegend=False, xaxis_title="", yaxis_title="分數總和")
                st.plotly_chart(fig_age_box, use_container_width=True)

        with age2:
            if '年齡層' in latest_tested_df.columns and '性別' in latest_tested_df.columns and '分數總和' in latest_tested_df.columns:
                age_gender_df = latest_tested_df.dropna(subset=['年齡層', '分數總和', '性別'])
                age_gender_avg = age_gender_df.groupby(['年齡層', '性別'])['分數總和'].mean().reset_index()
                age_gender_avg['分數總和'] = age_gender_avg['分數總和'].round(1)
                fig_age_gender = px.bar(
                    age_gender_avg, x='年齡層', y='分數總和', color='性別',
                    barmode='group', text='分數總和',
                    title="年齡層 × 性別 平均總分",
                    category_orders={'年齡層': ['20-29歲', '30-39歲', '40-49歲', '50歲以上']}
                )
                fig_age_gender.update_traces(textposition='outside')
                fig_age_gender.update_layout(xaxis_title="", yaxis_title="平均總分")
                st.plotly_chart(fig_age_gender, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 四、分隊訓練優先排行")
        if '分數總和' in latest_tested_df.columns:
            plan_filter_col, plan_chart_col = st.columns([1, 4])
            with plan_filter_col:
                selected_brigades_plan = st.multiselect(
                    "篩選大隊（空白顯示全部）：",
                    latest_tested_df['消防局大隊'].dropna().unique(),
                    key='plan_brigade'
                )
            plan_df = latest_tested_df if not selected_brigades_plan else latest_tested_df[latest_tested_df['消防局大隊'].isin(selected_brigades_plan)]

            unit_stats = plan_df.dropna(subset=['分數總和']).groupby(['消防局大隊', '分隊'])['分數總和'].agg(
                平均成績='mean', 最高成績='max', 最低成績='min', 人數='count'
            ).reset_index()
            unit_stats['平均成績'] = unit_stats['平均成績'].round(1)
            unit_stats = unit_stats.sort_values(by='平均成績', ascending=False)

            with plan_chart_col:
                fig_unit = px.bar(
                    unit_stats, x='分隊', y='平均成績', color='消防局大隊',
                    text='平均成績', title="分隊平均成績排行",
                    hover_data=['人數', '最高成績', '最低成績']
                )
                fig_unit.update_traces(textposition='outside')
                fig_unit.update_layout(xaxis_title="", yaxis_title="平均成績")
                st.plotly_chart(fig_unit, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 五、訓練建議")
        rec_tab1, rec_tab2, rec_tab3 = st.tabs(["🏷️ 項目別訓練建議", "👥 年齡層別建議", "📅 年度訓練計畫"])

        with rec_tab1:
            st.markdown("""
| 測驗項目 | 訓練建議 | 訓練方法 | 週訓次 |
|----------|----------|----------|--------|
| 1500公尺跑步 | 有氧耐力不足 | 有氧跑 / 間歇跑，每次20-30分鐘 | 週訓3次 |
| 懸吊屈體 | 上半身控制/核心不足 | 引體向上 + 核心控制，屈體夾腿動作 | 週訓2次 |
| 菱形槓硬舉 | 下背力量/爆發力不足 | 爆發力訓練/T型架硬舉，特殊輔助動作 | 週訓2次 |
| 立定跳遠 | 下肢爆發力不足 | 增強式訓練/波比訓練，半蹲爆發跳 | 週訓2次 |
| 後拋擲遠 | 核心爆發力不足 | 核心爆發力+T立式跑 | 週訓2次 |
| 折返跑 | 敏捷性/速耐力不足 | 敏捷梯 / 間歇短跑 / 折返加速訓練 | 週訓2次 |
| 負重行走 | 全身肌耐力不足 | 自我肌耐力 + 以kgBW計算有氧LSD路跑 | 週訓1次 |
""")
        with rec_tab2:
            st.markdown("""
| 年齡層 | 注意事項 | 訓練調整建議 |
|--------|----------|-------------|
| 20-29歲 | 高強度不容易，骨骼肌發育仍在成熟 | 以強化技巧為主，慢慢增強訓練量 |
| 30-39歲 | 體能下滑，結束運動後回復更慢 | 在週計劃保留恢復日 + 增強式訓練，避免過度訓練 |
| 40-49歲 | 肌力/心肺開始明顯下滑，較易積傷 | 中低強度有氧鞏固 + 月計劃週期訓練，積極使用恢復課程 |
| 50歲以上 | 訓練後恢復較慢，須特別重視代謝 | 訓練量減少，強度謹慎增加；積極使用伸展/靜態恢復課程 |
""")
            st.warning("⚠️ 訓練 50歲以上人員的訓練每一個月需降低一個強度（或降低里程），以避免運動傷害；建議由教練評估整體訓練規劃及身體狀況。")

        with rec_tab3:
            st.markdown("""
年度訓練週期建議（消防局體技能測驗）：

- 📅 建議每月測驗進度並繳交成績，讓各分隊了解自身狀況
- 📊 在測驗3個月前開始密集訓練，提升有針對性弱項的訓練比例
- ⚠️ 避免測驗前1週才開始衝刺訓練，以確保成績穩定表現
- 🏅 高分組（≥90分）可維持現有訓練強度，鼓勵帶動其他人進步（進步激勵機制）
""")

    # ===== Tab 8: 深度分析 =====
    with tab_stats:
        st.subheader("🔬 深度統計分析")
        st.caption("本頁提供相關性分析、BMI計算，以及特殊狀態人員追蹤。")
        analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["📐 項目相關性分析", "⚖️ BMI 計算", "🏥 特殊狀態追蹤"])

        with analysis_tab1:
            st.markdown("#### 📐 測驗項目間相關性矩陣")
            st.caption("顏色越深綠代表正相關，越深紅代表負相關。")

            all_score_cols_corr = [m + '_成績' for m in test_metrics if m + '_成績' in latest_tested_df.columns]
            if len(all_score_cols_corr) >= 2:
                corr_data = latest_tested_df[all_score_cols_corr].dropna()
                if len(corr_data) > 5:
                    corr_matrix = corr_data.corr()
                    corr_matrix.index = [c.replace('_成績', '') for c in corr_matrix.index]
                    corr_matrix.columns = [c.replace('_成績', '') for c in corr_matrix.columns]

                    fig_corr = go.Figure(data=go.Heatmap(
                        z=corr_matrix.values, x=corr_matrix.columns.tolist(), y=corr_matrix.index.tolist(),
                        colorscale='RdYlGn', zmin=-1, zmax=1,
                        text=corr_matrix.values.round(2), texttemplate='%{text}', textfont={"size": 12},
                    ))
                    fig_corr.update_layout(title=f"測驗項目成績相關性矩陣（n={len(corr_data)}）", height=500)
                    st.plotly_chart(fig_corr, use_container_width=True)
                    
                    # ✅ 修正點：使用 Pandas 內建方法取代雙層迴圈
                    st.markdown("高相關性項目對（|r| > 0.5）：")
                    corr_unstacked = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)).unstack().dropna()
                    high_corr_series = corr_unstacked[abs(corr_unstacked) > 0.5]
                    
                    if not high_corr_series.empty:
                        high_corr_df = high_corr_series.reset_index()
                        high_corr_df.columns = ['項目A', '項目B', '相關係數']
                        high_corr_df['相關係數'] = high_corr_df['相關係數'].round(3)
                        high_corr_df['關係'] = np.where(high_corr_df['相關係數'] > 0, '正相關', '負相關')
                        st.dataframe(high_corr_df.sort_values('相關係數', ascending=False), hide_index=True, use_container_width=True)
                    else:
                        st.info("沒有顯著高相關的項目對（|r| ≤ 0.5）。")
                else:
                    st.warning("資料不足，無法計算相關性矩陣。")

            st.markdown("---")
            st.markdown("#### 🔍 項目成績散點圖探索")
            metric_cols_available = [m for m in test_metrics if m + '_成績' in latest_tested_df.columns]
            if len(metric_cols_available) >= 2:
                sc1, sc2 = st.columns(2)
                with sc1: x_metric = st.selectbox("X軸項目", metric_cols_available, key='corr_x')
                with sc2: y_metric = st.selectbox("Y軸項目", metric_cols_available, index=min(1, len(metric_cols_available)-1), key='corr_y')

                if x_metric != y_metric:
                    scatter_df = latest_tested_df[[x_metric+'_成績', y_metric+'_成績', '消防局大隊', '姓名']].dropna()
                    if not scatter_df.empty:
                        fig_scatter = px.scatter(
                            scatter_df, x=x_metric+'_成績', y=y_metric+'_成績',
                            color='消防局大隊', hover_data=['姓名'],
                            title=f"{x_metric} vs {y_metric} 散點圖", trendline="ols"
                        )
                        st.plotly_chart(fig_scatter, use_container_width=True)

        with analysis_tab2:
            st.markdown("#### ⚖️ BMI 計算工具")
            height_col = next((c for c in df.columns if '身高' in c or 'height' in c.lower()), None)
            weight_col = next((c for c in df.columns if '體重' in c or 'weight' in c.lower()), None)

            if height_col and weight_col:
                bmi_df = latest_tested_df.copy()
                
                # ✅ 修正點：避免身高為 0 造成除以零崩潰
                weight_num = pd.to_numeric(bmi_df[weight_col], errors='coerce')
                height_m = pd.to_numeric(bmi_df[height_col], errors='coerce') / 100
                height_m = height_m.replace(0, np.nan)
                
                bmi_df['BMI'] = (weight_num / (height_m ** 2)).round(1)
                bmi_df = bmi_df.dropna(subset=['BMI'])

                def classify_bmi(bmi):
                    if bmi < 18.5: return '體重過輕'
                    elif bmi < 24: return '✅ 正常範圍'
                    elif bmi < 27: return '⚠️ 過重'
                    else: return '🔴 肥胖'

                bmi_df['BMI分類'] = bmi_df['BMI'].apply(classify_bmi)
                bmi_counts = bmi_df['BMI分類'].value_counts().reset_index()
                bmi_counts.columns = ['BMI分類', '人數']

                bc1, bc2 = st.columns(2)
                with bc1:
                    fig_bmi = px.pie(bmi_counts, names='BMI分類', values='人數', title="BMI分類分布")
                    st.plotly_chart(fig_bmi, use_container_width=True)
                with bc2:
                    if '分數總和' in bmi_df.columns:
                        fig_bmi_score = px.scatter(bmi_df, x='BMI', y='分數總和', color='BMI分類',
                                                   hover_data=['姓名'], title="BMI vs 總成績關係圖", trendline="ols")
                        st.plotly_chart(fig_bmi_score, use_container_width=True)
            else:
                st.info("📊 目前資料中無身高體重欄位，無法自動計算BMI。提供手動計算工具：")
                bmi_c1, bmi_c2 = st.columns(2)
                with bmi_c1:
                    manual_height = st.number_input("身高（公分）", min_value=140, max_value=220, value=170)
                    manual_weight = st.number_input("體重（公斤）", min_value=40, max_value=150, value=70)
                with bmi_c2:
                    manual_bmi = manual_weight / (manual_height / 100) ** 2
                    if manual_bmi < 18.5: bmi_status = "體重過輕"
                    elif manual_bmi < 24: bmi_status = "✅ 正常範圍"
                    elif manual_bmi < 27: bmi_status = "⚠️ 過重"
                    else: bmi_status = "🔴 肥胖"
                    st.metric("BMI值", f"{manual_bmi:.1f}")
                    st.write(f"BMI分類：{bmi_status}")

        with analysis_tab3:
            st.markdown("#### 🏥 特殊狀態人員追蹤")
            if not special_df.empty:
                show_cols = ['消防局大隊', '分隊', '姓名', '特殊狀態'] + [m + '_成績' for m in test_metrics if m + '_成績' in special_df.columns]
                show_cols = [c for c in show_cols if c in special_df.columns]
                st.dataframe(special_df[show_cols], hide_index=True, use_container_width=True)

                status_counts = special_df['特殊狀態'].value_counts().reset_index()
                status_counts.columns = ['狀態', '人數']
                fig_status = px.bar(status_counts, x='狀態', y='人數', text='人數',
                                    title="特殊狀態類型統計", color_discrete_sequence=['#6c757d'])
                fig_status.update_traces(textposition='outside')
                st.plotly_chart(fig_status, use_container_width=True)
            else:
                st.success("🎉 本次測驗無特殊狀態人員記錄。")

            st.markdown("---")
            st.markdown("#### ⬇️ 匯出完整資料")
            full_csv = latest_tested_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label=f"⬇️ 下載完整最新測驗資料 CSV（{latest_date}）",
                data=full_csv.encode('utf-8-sig'),
                file_name=f"體技能完整資料_{latest_date}.csv",
                mime="text/csv"
            )

else:
    st.info("資料載入中，請確認網路和資料來源是否正確...")
