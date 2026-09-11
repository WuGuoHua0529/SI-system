import traceback
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def check_jis_updates(items):
    """
    抓取 JIS 網站上的標準更新紀錄 (目前使用者提供的是 ANSI Webstore 網址)。
    
    :param items: list of dict, 包含 keyword 與 url
    :return: list of dict, 包含比對成功的更新紀錄
    """
    if not items:
        return []
        
    matched_updates = {}
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            for item in items:
                keyword = item['keyword'].strip()
                url = item['url'].strip()
                
                try:
                    if not url.startswith('http'):
                        matched_updates[url.lower()] = {
                            "keyword": url,
                            "procedure": keyword,
                            "change": "格式錯誤",
                            "date": "請輸入完整網址"
                        }
                        continue
                        
                    page.goto(url)
                    page.wait_for_timeout(3000)
                    
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 網頁標題通常包含標準編號與年份，例如：
                    # "JIS D 0203:1994 - Method of moisture, rain and spray test..."
                    title = soup.title.text.strip() if soup.title else ""
                    
                    # 方法一：從標題的冒號格式提取年份 (JIS X 0000:2024)
                    import re
                    year_match = re.search(r':(\d{4})', title)
                    
                    # 方法二：若冒號格式找不到，改從「Most recent」文字區塊找年份
                    if not year_match:
                        most_recent_div = soup.find(string=re.compile(r'Most recent', re.I))
                        if most_recent_div:
                            parent_text = most_recent_div.find_parent().get_text()
                            year_match = re.search(r':(\d{4})', parent_text)
                    
                    if year_match:
                        year = year_match.group(1)
                        date_str = year
                    else:
                        date_str = "查無年份資訊"
                    
                    matched_updates[keyword.lower()] = {
                        "keyword": keyword,
                        "date": date_str
                    }
                        
                except Exception as e:
                    print(f"JIS Scraper Error for {keyword}: {e}")
                    matched_updates[keyword.lower()] = {
                        "keyword": keyword,
                        "date": "無法取得"
                    }
            
            browser.close()
            
    except Exception as e:
        print(f"Playwright Initialization Error: {traceback.format_exc()}")
        
    return list(matched_updates.values())
