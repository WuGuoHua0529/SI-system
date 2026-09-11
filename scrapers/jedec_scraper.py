import re
from playwright.sync_api import sync_playwright

def check_jedec_updates(items):
    """
    抓取 JEDEC 網站上的標準更新紀錄。
    由於 JEDEC 網站可能有防爬蟲保護 (403 Forbidden)，我們使用 Playwright 來模擬真實瀏覽器。
    
    :param items: list of dict, 包含 keyword 與 url
    :return: list of dict, 包含比對成功的更新紀錄
    """
    if not items:
        return []
        
    matched_updates = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        
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
                page = context.new_page()
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                try:
                    page.wait_for_selector('h1', timeout=5000)
                except:
                    pass
                    
                # 抓取頁面上所有的純文字
                text = page.evaluate('document.body.innerText')
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                # 尋找 "Published:" 開頭的行
                date_str = "無法取得版本"
                for line in lines:
                    if line.startswith('Published:'):
                        date_str = line.replace('Published:', '').strip()
                        break
                        
                matched_updates[keyword.lower()] = {
                    "keyword": keyword,
                    "date": date_str
                }
                
                page.close()
            except Exception as e:
                print(f"JEDEC Scraper Error for {keyword}: {e}")
                matched_updates[keyword.lower()] = {
                    "keyword": keyword,
                    "date": "爬蟲發生錯誤"
                }
                
        browser.close()
        
    return list(matched_updates.values())
