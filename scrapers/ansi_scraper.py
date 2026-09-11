import traceback
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def check_ansi_updates(items):
    """
    抓取 ANSI 網站上的標準更新紀錄 (使用 Playwright 繞過 Cloudflare)。
    
    :param items: list of dict, 例如 [{'keyword': 'ANSI C136.31', 'url': 'https://webstore.ansi.org/search/find?st=...'}]
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
                keyword = item['keyword']
                url = item['url']
                
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
                    # 給一點時間讓網頁載入
                    page.wait_for_timeout(3000)
                    
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 尋找搜尋結果的連結
                    links = soup.find_all("a", href=True)
                    latest_version = None
                    
                    # 取出第一個符合關鍵字的連結文字，通常 ANSI 會標示為如 'ANSI C136.31-2023'
                    for l in links:
                        link_text = l.text.strip()
                        if keyword.upper() in link_text.upper():
                            latest_version = link_text
                            break
                            
                    if latest_version:
                        matched_updates[keyword.lower()] = {
                            "keyword": keyword,
                            "date": latest_version
                        }
                    else:
                        matched_updates[keyword.lower()] = {
                            "keyword": keyword,
                            "date": "查無資料"
                        }
                        
                except Exception as e:
                    print(f"ANSI Scraper Error for {keyword}: {e}")
                    matched_updates[keyword.lower()] = {
                        "keyword": keyword,
                        "date": "無法取得"
                    }
            
            browser.close()
            
    except Exception as e:
        print(f"Playwright Initialization Error: {traceback.format_exc()}")
        
    return list(matched_updates.values())
