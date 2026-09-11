import requests
from bs4 import BeautifulSoup

def check_en_updates(items):
    """
    抓取 EN (en-standard.eu) 網站上的標準更新紀錄。
    
    :param items: list of dict, 包含 keyword 與 url
    :return: list of dict, 包含比對成功的更新紀錄
    """
    if not items:
        return []
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 尋找 <span class="released">Released: 1992-11</span>
            released_span = soup.find('span', class_='released')
            
            if released_span:
                released_text = released_span.get_text(separator=' ', strip=True).replace('\xa0', ' ')
                clean_date = released_text.replace('Released:', '').strip()
                matched_updates[keyword.lower()] = {
                    "keyword": keyword,
                    "date": clean_date
                }
            else:
                matched_updates[keyword.lower()] = {
                    "keyword": keyword,
                    "date": "查無資料"
                }
                
        except Exception as e:
            print(f"EN Scraper Error for {keyword}: {e}")
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": "無法取得"
            }
            
    return list(matched_updates.values())
