import requests
import re
import json
from urllib.parse import urlparse, parse_qsl

def check_etsi_updates(items, debug_callback=None):
    """
    抓取 ETSI 網站上的標準更新紀錄 (透過隱藏的後端 API)。
    
    :param items: list of dict, 包含 keyword 與 url
    :return: list of dict, 包含比對成功的更新紀錄
    """
    if not items:
        return []
        
    # 我們不依賴使用者輸入的網址，而是直接打 API
    api_url = 'https://www.etsi.org/custom/standardssearch/data.php'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    matched_updates = {}
    
    for item in items:
        keyword = item['keyword'].strip()
        user_url = item.get('url', '').strip()
        
        # 解析使用者提供的網址 (可能包含在 # 後面，也可能在 ? 後面)
        parsed = urlparse(user_url)
        qs = parsed.fragment if parsed.fragment else parsed.query
        params = dict(parse_qsl(qs))
        
        # 若使用者網址中有參數，強制加上 format=json
        if params:
            params['format'] = 'json'
        else:
            # 如果沒有參數，使用預設的備案
            params = {
                'format': 'json',
                'search': keyword,
                'isCurrent': 1,
                'sort': 1
            }
        
        try:
            res = requests.get(api_url, params=params, headers=headers, timeout=15)
            res.raise_for_status()
            
            data = res.json()
            
            if debug_callback:
                debug_output = (
                    "====================================\n"
                    f"【查詢字串 (Keyword)】: {keyword}\n"
                    "====================================\n"
                    "【API 參數 Payload (由網址自動解析)】:\n"
                    f"{json.dumps(params, indent=2, ensure_ascii=False)}\n"
                    "====================================\n"
                    f"【API 回傳結果】 (共 {len(data)} 筆，顯示前 5 筆):\n"
                    f"{json.dumps(data[:5], indent=2, ensure_ascii=False)}\n\n"
                )
                debug_callback(debug_output)
            
            # 依照使用者要求，不進行萃取比對，直接拿 API 回傳的第一筆資料
            target_deliverable = None
            if isinstance(data, list) and len(data) > 0:
                target_deliverable = data[0].get('ETSI_DELIVERABLE', '')
                
                # 從 "ETSI EN 300 019-1-0 V2.1.2 (2003-09)" 中提取 "2003-09"
                m = re.search(r'\((\d{4}-\d{2})\)', target_deliverable)
                if m:
                    date_str = m.group(1)
                else:
                    date_str = target_deliverable # 若沒括號，則 fallback 顯示全字串
                
                matched_updates[keyword.lower()] = {
                    "keyword": keyword,
                    "date": date_str
                }
            else:
                matched_updates[keyword.lower()] = {
                    "keyword": keyword,
                    "date": "查無資料"
                }
                
        except Exception as e:
            print(f"ETSI API Error for {keyword}: {e}")
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": "無法取得"
            }
            
    return list(matched_updates.values())
