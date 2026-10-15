import pandas as pd

def export_excel_rules(file_path, rules):
    """
    將追蹤規則匯出為相容匯入格式的 Excel (.xlsx)。
    預期格式 (直欄):
    Platform | Standard_ID | URL | Current_Version
    """
    try:
        if not rules:
            return False, "目前沒有任何追蹤資料可匯出！"
        
        rows = []
        for r in rules:
            # 取得版本：若有爬蟲獲取到的最新版本且非空，以最新版本為主；否則保留前次基準
            latest = r.get("latestDocumentName")
            prev = r.get("previousDocumentName", "")
            current_ver = latest if (latest and latest != "無資料") else prev
            
            rows.append({
                "Platform": r.get("source", ""),
                "Standard_ID": r.get("name", ""),
                "URL": r.get("query", ""),
                "Current_Version": current_ver if current_ver else ""
            })
            
        df = pd.DataFrame(rows)
        df.to_excel(file_path, index=False, engine='openpyxl')
        return True, f"成功匯出 {len(rows)} 筆追蹤項目！"
    except Exception as e:
        return False, f"匯出失敗: {str(e)}"
