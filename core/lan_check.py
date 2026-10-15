import os
import threading


def check_lan(nas_folder, timeout=3.0):
    """
    檢查是否在公司區網內（能否存取 NAS 資料夾）。
    回傳: 'disabled' (未設定) / 'ok' / 'failed'
    網路路徑不通時 os.path.isdir 可能卡很久，所以放背景執行緒並設逾時。
    """
    if not nas_folder or not nas_folder.strip():
        return 'disabled'

    result = {'ok': False}

    def _probe():
        try:
            result['ok'] = os.path.isdir(nas_folder)
        except Exception:
            result['ok'] = False

    t = threading.Thread(target=_probe, daemon=True)
    t.start()
    t.join(timeout)
    return 'ok' if (not t.is_alive() and result['ok']) else 'failed'
