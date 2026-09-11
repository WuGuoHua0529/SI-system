import re

try:
    from DrissionPage import ChromiumPage, ChromiumOptions
except ImportError:
    ChromiumPage = None
    ChromiumOptions = None

def check_sae_updates(items):
    """
    抓取 SAE (saemobilus.sae.org) 網站上的標準更新紀錄。
    為避免防爬蟲機制導致逾時，改用 DrissionPage (背景模式)。
    """
    if not items:
        return []
        
    matched_updates = {}
    
    try:
        co = ChromiumOptions()
        co.set_argument('--headless')
        page = ChromiumPage(addr_or_opts=co)
    except Exception as e:
        print(f"DrissionPage 初始化失敗: {e}")
        return [{"keyword": item['keyword'].strip(), "date": "啟動失敗"} for item in items]
        
    for item in items:
        keyword = item.get('keyword', '').strip()
        url = item.get('url', '').strip()
        
        if not url:
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": "請提供網址"
            }
            continue
            
        try:
            page.get(url, timeout=30)
            
            # 給網頁一點時間載入文字
            page.wait(3)
                
            text = page.ele('tag:body').text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            date_str = "無法取得版本"
            
            # 策略一：尋找 "Additional Details" 區塊內的 "Published"
            additional_details_idx = -1
            for i, line in enumerate(lines):
                if 'Additional Details' in line:
                    additional_details_idx = i
                    break
            
            if additional_details_idx != -1:
                for i in range(additional_details_idx, min(len(lines), additional_details_idx + 100)):
                    if lines[i] == 'Published':
                        if i + 1 < len(lines):
                            date_str = lines[i + 1].replace('\xa0', '').strip()
                        break
            
            # 策略二：如果策略一沒找到，回到最上方找標題下方的狀態
            if date_str == "無法取得版本":
                for i, line in enumerate(lines):
                    if line in ['Published', 'Revised', 'Issued', 'Reaffirmed', 'Stabilized']:
                        if i + 1 < len(lines):
                            date_str = lines[i + 1].replace('\xa0', '').strip()
                        break
                    
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": date_str
            }
            
        except Exception as e:
            print(f"SAE Scraper Error for {keyword}: {e}")
            matched_updates[keyword.lower()] = {
                "keyword": keyword,
                "date": "爬蟲發生錯誤"
            }
            
    try:
        page.quit()
    except:
        pass
        
    return list(matched_updates.values())
