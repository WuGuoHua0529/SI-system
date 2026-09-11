import requests
from bs4 import BeautifulSoup

def check_ista_updates(items):
    """
    抓取 ISTA 網站上的程序變更紀錄，並比對使用者的追蹤關鍵字。
    
    :param items: list of dict, 例如 [{'keyword': '1A', 'url': 'https://ista.org/procedure_changes_developmen.php'}]
    :return: list of dict, 包含比對成功的更新紀錄
    """
    if not items:
        return []
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 由於多個關鍵字可能共用同一個網址，我們先依據網址來分組
    url_to_keywords = {}
    for item in items:
        kw = item['keyword']
        url = item['url']
        if url not in url_to_keywords:
            url_to_keywords[url] = []
        url_to_keywords[url].append(kw)
        
    matched_updates = {}
    
    for url, keywords in url_to_keywords.items():
        url = url.strip()
        
        if not url.startswith('http'):
            for kw in keywords:
                matched_updates[kw.lower()] = {
                    "keyword": kw,
                    "procedure": kw,
                    "change": "格式錯誤",
                    "date": "請輸入完整網址"
                }
            continue
            
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, 'html.parser')
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                    
                    if len(cols) >= 4:
                        procedure = cols[0]
                        change = cols[1]
                        type_of_change = cols[2]
                        date = cols[3]
                        
                        if "PROCEDURE" in procedure.upper():
                            continue
                            
                        for keyword in keywords:
                            keyword_lower = keyword.lower()
                            if keyword_lower in procedure.lower():
                                if keyword_lower not in matched_updates:
                                    matched_updates[keyword_lower] = {
                                        "keyword": keyword,
                                        "procedure": procedure,
                                        "change": change,
                                        "date": date
                                    }
        except Exception as e:
            print(f"ISTA Scraper Error for {url}: {e}")
            for kw in keywords:
                matched_updates[kw.lower()] = {
                    "keyword": kw,
                    "procedure": kw,
                    "change": "發生錯誤",
                    "date": "無法取得"
                }
                
    return list(matched_updates.values())
