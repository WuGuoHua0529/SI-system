import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_iec_updates(items):
    """
    抓取 IEC 網站上的標準更新紀錄。
    此網站防護較寬鬆，因此使用超高速的 Requests 爬蟲 (ISTA 模式)。
    
    :param items: list of dict, 包含 keyword 與 url
    :return: list of dict, 包含比對成功的更新紀錄
    """
    if not items:
        return []
        
    matched_updates = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for item in items:
        keyword = item['keyword'].strip()
        url = item['url'].strip()
        
        if not url:
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": "請提供網址"
            }
            continue
            
        try:
            res = requests.get(url, headers=headers, verify=False, timeout=15)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                text_content = soup.get_text(separator='\n', strip=True)
                lines = text_content.split('\n')
                
                date_str = ""
                for i, line in enumerate(lines):
                    if line == 'Publication date':
                        if i + 1 < len(lines):
                            date_str = lines[i+1].strip()
                        break
                        
                if date_str:
                    matched_updates[keyword.lower()] = {
                        "keyword": keyword,
                        "date": date_str
                    }
                else:
                    matched_updates[keyword.lower()] = {
                        "keyword": keyword,
                        "date": "找不到發布日期"
                    }
            else:
                matched_updates[keyword.lower()] = {
                    "keyword": keyword,
                    "date": f"連線錯誤: {res.status_code}"
                }
                
        except Exception as e:
            print(f"IEC Scraper Error for {keyword}: {e}")
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": "爬蟲發生錯誤"
            }
            
    return list(matched_updates.values())
