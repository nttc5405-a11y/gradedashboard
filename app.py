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

st.title("🚒 成功消防大隊 - 體技能戰情室 3.0 (分數權重版)")

@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["sheet_url"]
        df = pd.read_csv(url)
        
        # --- 魔法 1：精準清除底部的空白列 (不再誤刪分數列) ---
        # 找到最後一個有填寫「姓名」的列索引，再加一列就是該員的分數列
        last_valid_idx = df['姓名'].last_valid_index()
        if last_valid_idx is not None:
            df = df.iloc[:last_valid_idx + 2].copy()
            
        df = df.reset_index(drop=True)
        
        # 測驗日期防呆
        if '測驗日期' not in df.columns:
            df['測驗日期'] = '本次測驗'
            
        # --- 魔法 2：處理向下填滿 (Forward Fill) ---
        # 將包含特定關鍵字的欄位列為不屬於單項測驗的欄位
        meta_cols = [c for c in df.columns if '合計' in c or '總成績' in c or '備註' in c]
        ffill_cols = ['NO.', '單位', '姓名', '性別', '年齡', '測驗日期'] + meta_cols
        
        existing_cols = [c for c in ffill_cols if c in df.columns]
        df[existing_cols] = df[existing_cols].ffill()
        
        # --- 魔法 3：區分「紀錄」與「分數」 ---
        # 此時 DataFrame 已經很乾淨，0, 2, 4列絕對是紀錄，1, 3, 5列絕對是分數
        df['資料類型'] = np.where(df.index % 2 == 0, '紀錄', '分數')
        
        # --- 魔法 4：自動抓取「單項測驗項目」 ---
        KNOWN_COLS = ['NO.', '單位', '姓名', '性別', '年齡', '測驗日期', '資料類型', '年齡層']
        test_metrics = [c for c in df.columns if c not in KNOWN_COLS 
                        and '合計' not in c 
                        and '總成績' not in c 
                        and '備註' not in c 
                        and not str(c).startswith('Unnamed')]
        
        # 轉換數值格式
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
    
    # 拆分資料集
    df_score = df[df['資料類型'] == '分數'].copy()
    df_record = df[df['資料類型'] == '紀錄'].copy()
    
    # 過濾出「實際有測驗分數」的名單 (避免將空列算入平均)
    df_score_tested = df_score.dropna(subset=test_metrics, how='all')
    
    analysis_options = test_metrics + [c for c in meta_cols if '備註' not in c]
    
    k1, k2, k3, k4 = st.columns(4)
    latest_tested_df = df_score_tested[df_score_tested['測驗日期'] == latest_date]
    
    with k1: st.metric("本次實際測驗人數", f"{latest_tested_df['姓名'].nunique()} 人")
    with k2: st.metric("單項測驗數", f"{len(test_metrics)} 項")
    with k3: st.metric("受測單位數", f"{latest_tested_df['單位'].nunique()} 個")
    with k4: st.metric("最新測驗日期", f"{latest_date}")

    tab_overview, tab_group, tab_individual, tab_alert = st.tabs([
        "📊 戰情總覽 (分數)", "🔍 交叉分析 (分數)", "🎯 個人雷達 (分數)", "🚨 自訂警示"
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
            fig_line = px.line(trend_df, x='測驗日期', y=selected_metric, markers=True, 
                               title=f"大隊 {selected_metric} 歷次平均得分趨勢")
            st.plotly_chart(fig_line, use_container_width=True)

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

    # --- Tab 3: 個人追蹤儀表 ---
    with tab_individual:
        cp1, cp2 = st.columns([1, 2])
        with cp1:
            p_name = st.selectbox("選擇隊員", df['姓名'].dropna().unique())
            
            p_scores = df_score[df_score['姓名'] == p_name].sort_values(by='測驗日期', ascending=False)
            p_records = df_record[df_record['姓名'] == p_name].sort_values(by='測驗日期', ascending=False)
            
            # 加入防呆機制：確保該員確實有紀錄可供讀取
            if not p_scores.empty and not p_records.empty:
                p_score_latest = p_scores.iloc[0]
                p_record_latest = p_records.iloc[0]
                
                st.info(f"姓名： {p_score_latest['姓名']} | 單位： {p_score_latest['單位']} | 總成績： {p_score_latest.get('總成績', '無資料')}")
                
                remark_cols = [c for c in df.columns if '備註' in c]
                if remark_cols and pd.notna(p_score_latest[remark_cols[0]]):
                    st.warning(f"📝 備註事項： {p_score_latest[remark_cols[0]]}")
                
                st.write("最新成績明細 (紀錄 / 分數)：")
                for m in test_metrics:
                    rec_val = p_record_latest[m] if pd.notna(p_record_latest[m]) else "-"
                    score_val = p_score_latest[m] if pd.notna(p_score_latest[m]) else "-"
                    st.write(f"- **{m}**： {rec_val} / 得 {score_val} 分")
                    
        with cp2:
            if not p_scores.empty:
                radar_scores = []
                valid_metrics = []
                
                for m in test_metrics:
                    val = p_score_latest[m]
                    if pd.notna(val):
                        latest_all = df_score_tested[df_score_tested['測驗日期'] == latest_date][m].dropna()
                        if len(latest_all) > 0:
                            pr = (latest_all <= val).mean() * 100
                            radar_scores.append(pr)
                            valid_metrics.append(m)

                if len(valid_metrics) > 2:
                    radar_df = pd.DataFrame({'項目': valid_metrics, 'PR值 (受測母體百分等級)': radar_scores})
                    fig_radar = px.line_polar(radar_df, r='PR值 (受測母體百分等級)', theta='項目', line_close=True, range_r=[0, 100])
                    fig_radar.update_traces(fill='toself', line_color='#FF4B4B')
                    st.plotly_chart(fig_radar, use_container_width=True)
                    st.markdown("<span style='font-size:12px; color:gray;'>*註：雷達圖顯示為得點的 PR 值，100 分代表該項得分為大隊最高。*</span>", unsafe_allow_html=True)
                else:
                    st.warning("該員有效成績項目不足，無法繪製雷達圖 (可能為未測驗)。")
            else:
                st.error("系統讀取不到該員的分數紀錄。")

    # --- Tab 4: 自訂警示區 ---
    with tab_alert:
        ca1, ca2 = st.columns(2)
        with ca1:
            st.markdown("##### 🔥 自訂退步監控 (以分數計算)")
            reg_m = st.selectbox("監控退步項目：", analysis_options, key='al_r1')
            reg_val = st.number_input("容許退步空間 (減少幾分)：", value=10)
            
            if len(all_dates) > 1:
                d_now = df_score_tested[df_score_tested['測驗日期']==all_dates[0]][['姓名', '單位', reg_m]]
                d_old = df_score_tested[df_score_tested['測驗日期']==all_dates[1]][['姓名', reg_m]]
                merged = pd.merge(d_now, d_old, on='姓名', suffixes=('_今', '_昨')).dropna()
                
                merged['退步幅度'] = merged[f'{reg_m}_昨'] - merged[f'{reg_m}_今']
                regression = merged[merged['退步幅度'] > reg_val].sort_values(by='退步幅度', ascending=False)
                
                if not regression.empty:
                    st.dataframe(regression[['姓名', '單位', '退步幅度']], hide_index=True, use_container_width=True)
                else:
                    st.success("🎉 無人觸發退步警示！")
            else:
                st.info("資料不足兩次測驗，無法比對退步狀況。")

        with ca2:
            st.markdown("##### ❌ 自訂未達標監控 (以分數計算)")
            fail_m = st.selectbox("監控達標項目：", analysis_options, key='al_f1')
            fail_val = st.number_input("最低及格標準 (分數)：", value=60)
            
            fail_list = df_score_tested[(df_score_tested['測驗日期']==latest_date) & (df_score_tested[fail_m] < fail_val)]
                
            if not fail_list.empty:
                st.dataframe(fail_list[['姓名', '單位', fail_m]], hide_index=True, use_container_width=True)
            else:
                st.success("🎉 實際受測者皆通過此項目標準！")
else:
    st.info("等待讀取資料庫...")
