import requests
from bs4 import BeautifulSoup
import urllib3

# 停用不安全憑證警告 (避免某些舊版網站 TLS 報錯)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_telcordia_updates(items):
    """
    抓取 Telcordia (Ericsson depot) 網站上的標準更新紀錄。
    此網站沒有嚴格的防火牆防護，因此我們使用超高速的 Requests 爬蟲 (ISTA 模式)！
    
    :param items: list of dict, 包含 keyword 與 url
    :return: list of dict, 包含比對成功的更新紀錄
    """
    if not items:
        return []
        
    matched_updates = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
                
                doc_num = ""
                issue_num = ""
                issue_date = ""
                
                for i, line in enumerate(lines):
                    if line == 'Document Number':
                        if i + 1 < len(lines):
                            doc_num = lines[i+1].strip()
                    elif line == 'Issue Number':
                        if i + 1 < len(lines):
                            issue_num = lines[i+1].strip()
                    elif line == 'Issue Date':
                        if i + 1 < len(lines):
                            issue_date = lines[i+1].strip()
                        
                if issue_date:
                    # 只要 Dec 2017 這種格式就好
                    version_str = issue_date
                    matched_updates[keyword.lower()] = {
                        "keyword": keyword,
                        "date": version_str.strip()
                    }
                else:
                    matched_updates[keyword.lower()] = {
                        "keyword": keyword,
                        "date": "找不到版本資訊"
                    }
            else:
                matched_updates[keyword.lower()] = {
                    "keyword": keyword,
                    "date": f"連線錯誤: {res.status_code}"
                }
                
        except Exception as e:
            print(f"Telcordia Scraper Error for {keyword}: {e}")
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": "爬蟲發生錯誤"
            }
            
    return list(matched_updates.values())
