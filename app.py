# --- Tab 1: 大隊戰情總覽 (優化：加入項目切換與全項目趨勢) ---
    with tab_overview:
        # 在分頁頂部加入項目選擇器
        st.subheader("📊 大隊訓練績效總覽")
        selected_metric = st.selectbox(
            "請選擇欲分析的測驗項目：", 
            ['3000公尺跑步_秒', '引體向上_下', '負重爬梯_秒', '繩索救援_分數'],
            key='overview_metric'
        )
        
        st.markdown(f"目前顯示：**{selected_metric}** 的數據分析")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown(f"**各分隊平均成績**")
            # 根據選擇項目計算各分隊平均值
            avg_data = df.groupby('分隊')[selected_metric].mean().reset_index()
            fig_bar = px.bar(
                avg_data, 
                x='分隊', 
                y=selected_metric, 
                color='分隊', 
                text_auto='.1f',
                title=f"各分隊 {selected_metric} 表現"
            )
            fig_bar.update_layout(showlegend=False)
            # 如果是秒數項目，Y軸反轉(越低越好)
            if '秒' in selected_metric:
                fig_bar.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_bar, use_container_width=True)

        with c2:
            st.markdown(f"**大隊歷次成績趨勢**")
            # 根據選擇項目計算大隊歷次測驗平均值
            trend = df.groupby('測驗日期')[selected_metric].mean().reset_index()
            fig_line = px.line(
                trend, 
                x='測驗日期', 
                y=selected_metric, 
                markers=True,
                title=f"全大隊 {selected_metric} 隨時間變化趨勢"
            )
            
            # 智慧型 Y 軸反轉
            if '秒' in selected_metric:
                fig_line.update_yaxes(autorange="reversed")
                st.markdown("<span style='font-size:12px; color:gray;'>*註：折線向上代表秒數減少 (進步)*</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='font-size:12px; color:gray;'>*註：折線向上代表分數/次數增加 (進步)*</span>", unsafe_allow_html=True)
                
            st.plotly_chart(fig_line, use_container_width=True)

        # 額外小驚喜：顯示該項目的全大隊最高與最低紀錄
        col_stat1, col_stat2 = st.columns(2)
        best_val = df[selected_metric].min() if '秒' in selected_metric else df[selected_metric].max()
        worst_val = df[selected_metric].max() if '秒' in selected_metric else df[selected_metric].min()
        
        st.info(f"💡 **歷史紀錄小看板**：在【{selected_metric}】項目中，全大隊最佳紀錄為 **{best_val:.1f}**，最需要加油的紀錄為 **{worst_val:.1f}**。")
