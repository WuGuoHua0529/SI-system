import re

# 英文月份名稱對照表 (含常見拼字錯誤)
MONTH_MAP = {
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
    'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
    'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    'january': '01', 'february': '02', 'march': '03', 'april': '04',
    'june': '06', 'july': '07', 'august': '08', 'september': '09',
    'october': '10', 'november': '11', 'december': '12',
    'ocotber': '10' # 處理常見拼寫錯誤
}

def normalize_date(date_str):
    """
    將各種日期格式標準化為 yyyy/mm/dd，缺失的部分以 -- 補充。
    
    支援的輸入格式：
    - yyyy-mm-dd / yyyy/mm/dd   → yyyy/mm/dd
    - mm/dd/yyyy (美式)          → yyyy/mm/dd
    - yyyy-mm / yyyy/mm         → yyyy/mm/--
    - yyyy                      → yyyy/--/--
    - Dec 2017 / December 2017 / April2018 (含無空白) → yyyy/mm/--
    - 2025/03 等                → yyyy/mm/--
    """
    if not date_str:
        return date_str
    
    date_str = str(date_str).strip()
    
    # 系統保留值，不處理
    if date_str in ["無資料", "尚未檢查", "nan", "N/A", "", "找不到版本資訊", "找不到發布日期"]:
        return date_str

    # 1. yyyy-mm-dd 或 yyyy/mm/dd（完整日期）
    m = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$', date_str)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        return f"{y} / {mo} / {d}"

    # 2. mm/dd/yyyy 或 m/d/yyyy（美式格式，如 RTCA: 12/16/2014, SAE: 5/1/2025）
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', date_str)
    if m:
        mo, d, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{y} / {mo} / {d}"

    # 3. yyyy-mm 或 yyyy/mm（只有年月）
    m = re.match(r'^(\d{4})[-/](\d{1,2})$', date_str)
    if m:
        y, mo = m.group(1), m.group(2).zfill(2)
        return f"{y} / {mo} / --"

    # 4. 只有年份
    m = re.match(r'^(\d{4})$', date_str)
    if m:
        return f"{m.group(1)} / -- / --"

    # 5. "Dec 2017", "December 2017", "April2018"（英文月份在前，可能無空白）
    m = re.match(r'^([a-zA-Z]+)\s*(\d{4})$', date_str)
    if m:
        month_name = m.group(1).lower()
        year = m.group(2)
        month_num = MONTH_MAP.get(month_name)
        if month_num:
            return f"{year} / {month_num} / --"

    # 6. "2017 Dec" 或 "2017 December" / "2017Dec"（英文月份在後）
    m = re.match(r'^(\d{4})\s*([a-zA-Z]+)$', date_str)
    if m:
        year = m.group(1)
        month_name = m.group(2).lower()
        month_num = MONTH_MAP.get(month_name)
        if month_num:
            return f"{year} / {month_num} / --"

    # 7. "Jan 19, 2026" 或 "January 19, 2026"（美式帶日期的英文月份）
    m = re.match(r'^([a-zA-Z]+)\s*(\d{1,2})\s*,\s*(\d{4})$', date_str)
    if m:
        month_name = m.group(1).lower()
        day = m.group(2).zfill(2)
        year = m.group(3)
        month_num = MONTH_MAP.get(month_name)
        if month_num:
            return f"{year} / {month_num} / {day}"

    # 8. "16-JAN-1996" 或 "18-MAY-2022"（MIL quicksearch 的 dd-MMM-yyyy 格式）
    m = re.match(r'^(\d{1,2})\s*-\s*([a-zA-Z]{3})\s*-\s*(\d{4})$', date_str)
    if m:
        day = m.group(1).zfill(2)
        month_name = m.group(2).lower()
        year = m.group(3)
        month_num = MONTH_MAP.get(month_name)
        if month_num:
            return f"{year} / {month_num} / {day}"

    # 9. "1 August 2021" 或 "01 Aug 2021"（英式日期格式 DD Month YYYY）
    m = re.match(r'^(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})$', date_str)
    if m:
        day = m.group(1).zfill(2)
        month_name = m.group(2).lower()
        year = m.group(3)
        month_num = MONTH_MAP.get(month_name)
        if month_num:
            return f"{year} / {month_num} / {day}"

    # 10. 標準編號尾端帶年份，如 "ANSI C136.31-2023"、"ISO 9001:2015"
    #     優先取冒號或連字號後方的 4 位數年份（1900~2099）
    m = re.search(r'[-:]((19|20)\d{2})$', date_str)
    if m:
        return f"{m.group(1)} / -- / --"

    # 無法解析，原樣回傳
    return date_str
