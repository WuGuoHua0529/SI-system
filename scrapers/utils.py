from contextlib import contextmanager
from playwright.sync_api import sync_playwright

@contextmanager
def get_playwright_page(headless=True, timeout=30000):
    """
    提供一個已經設定好基本 User-Agent 與防阻擋特徵的 Playwright Page 對象。
    使用 context manager 自動管理 browser 和 context 的開關。
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        page.set_default_timeout(timeout)
        try:
            yield page
        finally:
            context.close()
            browser.close()
