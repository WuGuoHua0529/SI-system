import requests
import re
from bs4 import BeautifulSoup

def check_astm_updates(items):
    """
    抓取 ASTM 網站上的標準更新紀錄。
    
    :param items: list of dict, 包含 keyword 與 url
    :return: list of dict, 包含比對成功的更新紀錄
    """
    if not items:
        return []
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    matched_updates = {}
    
    for item in items:
        keyword = item['keyword'].strip()
        url = item['url'].strip()
        
        if not url.startswith('http'):
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": "必須是完整網址"
            }
            continue
            
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            
            # 從網頁中尋找 Last Updated 日期 (例如: Last Updated: Jan 19, 2026)
            latest_version = None
            date_match = re.search(r'Last Updated:\s*([A-Za-z]+\s+\d+,\s+\d{4})', res.text, re.I)
            
            if date_match:
                latest_version = date_match.group(1).strip()
            
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": latest_version if latest_version else "查無資料"
            }
                
        except Exception as e:
            print(f"ASTM Scraper Error for {keyword}: {e}")
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": "無法取得"
            }
            
    return list(matched_updates.values())
