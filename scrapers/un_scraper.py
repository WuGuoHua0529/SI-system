import re
import time

try:
    from seleniumbase import SB
except ImportError:
    SB = None

def check_un_updates(items):
    """
    抓取 UN 網站相關標準更新紀錄 (半自動互動版)
    
    機制：使用 SeleniumBase (UC Mode) 打開原本的 UNECE 網址，
    並顯示瀏覽器視窗。如果遇到 Cloudflare 阻擋，使用者可手動點擊驗證。
    爬蟲會持續等待直到真正進入網頁，再提取年份並自動關閉。
    """
    if not items:
        return []

    if SB is None:
        return [{"keyword": item['keyword'].strip(), "date": "缺少 SeleniumBase 套件"} for item in items]

    matched_updates = {}

    try:
        # headless=False: 強制顯示瀏覽器視窗讓使用者手動驗證
        with SB(uc=True, headless=False) as sb:
            for item in items:
                keyword = item.get('keyword', '').strip()
                url = item.get('url', '').strip()
                
                if not keyword or not url:
                    continue

                try:
                    # 開啟原始網址
                    sb.uc_open_with_reconnect(url, 4)
                    
                    # 給予一點時間讓 Cloudflare 載入
                    sb.sleep(2)
                    
                    # 自動嘗試點擊驗證碼 (輔助)
                    try:
                        sb.uc_gui_click_captcha()
                    except:
                        pass

                    # 進入最長 45 秒的等待迴圈，給予使用者充分時間點擊驗證
                    # 判斷標準：標題不再包含 Cloudflare 的特定字眼
                    cf_keywords = ["just a moment", "attention required", "unece.org"]
                    for _ in range(45):
                        title_text = sb.get_title().lower()
                        if title_text and not any(kw in title_text for kw in cf_keywords):
                            break
                        sb.sleep(1)
                    
                    # 確保頁面內容已載入
                    sb.sleep(2)
                    
                    # 獲取最終的標題與 h1
                    title_text = sb.get_title()
                    h1_text = ""
                    if sb.is_element_present("h1"):
                        h1_text = sb.get_text("h1")

                    target_text = h1_text if h1_text else title_text

                    # 從標題中提取括號內的年份，例如 Rev.8 (2023)
                    years = re.findall(r'\((20[12]\d)\)', target_text)
                    if not years:
                        years = re.findall(r'\b(20[12]\d)\b', target_text)

                    if years:
                        latest_year = str(max(int(y) for y in years))
                        final_date = latest_year
                    else:
                        title_lower = title_text.lower()
                        if any(kw in title_lower for kw in cf_keywords):
                            final_date = "驗證逾時或失敗"
                        else:
                            final_date = "無法取得版本"

                    matched_updates[keyword.lower()] = {
                        "keyword": keyword, 
                        "date": final_date
                    }

                except Exception as e:
                    print(f"UN Scraper Error for '{keyword}': {e}")
                    matched_updates[keyword.lower()] = {
                        "keyword": keyword, 
                        "date": "爬蟲發生錯誤"
                    }

    except Exception as e:
        print(f"SeleniumBase 初始化失敗: {e}")
        return [{"keyword": item['keyword'].strip(), "date": "瀏覽器啟動失敗"} for item in items]

    return list(matched_updates.values())

