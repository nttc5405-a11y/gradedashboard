@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        url = st.secrets["https://docs.google.com/spreadsheets/d/e/2PACX-1vQcsv0lMJmU68FYuyXRY6H4T9j9j8xgaC9xnSWwrCGbSuqACG1geXM34e-nvimhVQ/pub?gid=1434005373&single=true&output=csv"]
        
        # 1. 略過最上方第一行的合併大標題
        raw_df = pd.read_csv(url, header=None, skiprows=1)
        
        # 2. 處理雙層表頭 (Row 0: 測驗項目, Row 1: 欄位細項)
        main_headers = raw_df.iloc[0].ffill() # 橫向填充大項目，例如把「立定跳遠」填滿後面的空欄
        sub_headers = raw_df.iloc[1].fillna('')
        
        new_cols = []
        for m, s in zip(main_headers, sub_headers):
            m = str(m).strip()
            s = str(s).strip()
            # 濾除無效字眼
            if m.startswith('Unnamed') or m == 'nan': m = ''
            if s == 'nan': s = ''
            
            # 組合出如 "立定跳遠_成績" 或 "1500公尺跑步_總秒數" 的新欄位名
            if m and s and m != s:
                new_cols.append(f"{m}_{s}")
            elif m:
                new_cols.append(m)
            else:
                new_cols.append(s)
                
        # 3. 套用新表頭，並切掉前兩行的表頭列
        df = raw_df.iloc[2:].copy()
        df.columns = new_cols
        df = df.reset_index(drop=True)
        
        # 4. 防呆清理：濾除空白列或沒有名字的廢資料
        df = df.dropna(how='all')
        df = df.dropna(subset=['姓名'])
        
        # 自動識別有「_成績」結尾的欄位做為測驗項目
        score_cols = [c for c in df.columns if str(c).endswith('_成績')]
        test_metrics = [c.replace('_成績', '') for c in score_cols]
        
        # 5. 將成績欄位與年齡轉為數值型態 (以利畫圖計算)
        numeric_cols = score_cols + ['年齡', '分數總和']
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
                
        # 6. 年齡層分級
        bins = [20, 30, 40, 50, 70]
        labels = ['20-29歲', '30-39歲', '40-49歲', '50歲以上']
        df['年齡層'] = pd.cut(df['年齡'], bins=bins, labels=labels, right=False)
        
        # 7. 補上測驗日期 (如果新表沒有的話，先給個預設值)
        if '測驗日期' not in df.columns:
            df['測驗日期'] = '114年下半年'
            
        return df, test_metrics, score_cols
        
    except Exception as e:
        st.error(f"資料讀取失敗，請檢查。錯誤訊息：{e}")
        return None, [], []
