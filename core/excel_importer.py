import pandas as pd
from core.date_utils import normalize_date

def import_excel_rules(file_path, store):
    """
    從 Excel 檔案匯入追蹤規則。
    預期格式 (直欄):
    Platform (處理合併儲存格) | Standard_ID | URL | Current_Version
    """
    try:
        # 使用 openpyxl 讀取 (支援 .xlsx)
        df = pd.read_excel(file_path, engine='openpyxl')
        
        cols = df.columns.tolist()
        if len(cols) < 4:
            return False, "Excel 欄位不足，請確認格式包含 Platform, Standard_ID, URL, Current_Version"
            
        platform_col = cols[0]
        id_col = cols[1]
        url_col = cols[2]
        version_col = cols[3]
        
        # 向下遞補 Platform，解決 Excel 合併儲存格造成的 NaN 問題
        df[platform_col] = df[platform_col].ffill()
        
        imported_count = 0
        skipped_count = 0
        missing_urls = []
        
        for index, row in df.iterrows():
            platform_val = str(row[platform_col]).strip() if pd.notna(row[platform_col]) else ""
            keyword_val = str(row[id_col]).strip() if pd.notna(row[id_col]) else ""
            url_val = str(row[url_col]).strip() if pd.notna(row[url_col]) else ""
            version_val = str(row[version_col]).strip() if pd.notna(row[version_col]) else ""
            
            # 使用 mapping 處理大小寫慣例，找不到就直接 upper()
            SOURCE_NAME_MAP = {
                "TELCORDIA": "Telcordia", "IEC": "IEC", "ISTA": "ISTA",
                "ANSI": "ANSI", "ASTM": "ASTM", "DIN": "DIN", "ETSI": "ETSI",
                "EN": "EN", "ISO": "ISO", "JEDEC": "JEDEC", "JIS": "JIS",
                "MIL": "MIL", "RTCA": "RTCA", "SAE": "SAE", "DNV": "DNV", "UN": "UN"
            }
            
            # 完全空白的列 (或表頭) 就直接跳過
            if (not platform_val and not keyword_val) or keyword_val == "nan":
                continue
                
            source = SOURCE_NAME_MAP.get(platform_val.upper(), platform_val.upper())

            # 發現缺少網址的資料，記錄下來並跳過
            if not url_val or url_val == "nan":
                missing_urls.append(f"分類: {source} | 追蹤: {keyword_val} | 原因: 缺少網址")
                continue
            
            # 檢查是否已存在
            existing_rules = store.get_rules_by_source(source)
            exists = any(r['name'].lower() == keyword_val.lower() for r in existing_rules)
            
            if not exists:
                # 使用 store 標準方法新增，避免 id 衝突
                new_rule = store.add_rule(keyword_val, url_val, source)
                
                # 如果 Excel 有版本資訊，回填到 previousDocumentName
                if version_val and version_val != "nan":
                    new_rule["previousDocumentName"] = normalize_date(version_val)
                    store.update_rule(new_rule)
                    
                imported_count += 1
            else:
                skipped_count += 1
                
        msg = f"匯入成功！共新增 {imported_count} 筆追蹤 (略過 {skipped_count} 筆重複資料)。"
        if missing_urls:
            msg += f"\n\n⚠ 注意：有 {len(missing_urls)} 筆資料缺少網址未匯入：\n"
            if len(missing_urls) > 15:
                msg += "\n".join(missing_urls[:15])
                msg += f"\n... 以及其他 {len(missing_urls) - 15} 筆"
            else:
                msg += "\n".join(missing_urls)

        return True, msg
        
    except Exception as e:
        return False, f"匯入失敗: {str(e)}"
