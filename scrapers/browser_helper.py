def launch_browser(p, headless=True):
    """
    依序嘗試啟動瀏覽器：
    1. 首選：使用者電腦已安裝的 Google Chrome (channel="chrome")
    2. 次選：Windows 內建的 Microsoft Edge (channel="msedge")
    3. 備援：Playwright 預設核心 (若本機開發環境有安裝)
    若皆無法啟動，拋出明確的中文錯誤提示。
    """
    # 1. 首選：Google Chrome
    try:
        return p.chromium.launch(headless=headless, channel="chrome")
    except Exception:
        pass

    # 2. 次選：Microsoft Edge
    try:
        return p.chromium.launch(headless=headless, channel="msedge")
    except Exception:
        pass

    # 3. 備援：Playwright 預設核心
    try:
        return p.chromium.launch(headless=headless)
    except Exception:
        pass

    # 4. 若皆無可用瀏覽器，提示使用者
    raise RuntimeError(
        "未偵測到可用的瀏覽器！\n\n"
        "系統已嘗試搜尋 Google Chrome 與 Microsoft Edge 皆無法啟動。\n"
        "請確認電腦中已安裝 Google Chrome 或 Microsoft Edge 瀏覽器。"
    )
