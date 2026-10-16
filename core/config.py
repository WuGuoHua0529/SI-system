import json
import os
import sys

APP_VERSION = "1.0"

DEFAULT_CONFIG = {
    # 公司 NAS 共用資料夾 (例如 \\NAS01\SIS)。留空 = 不啟用區網檢查，帳號改存本機
    "nas_folder": ""
}


def get_app_dir():
    """打包後回傳 exe 所在資料夾；開發時回傳專案資料夾"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_path():
    return os.path.join(get_app_dir(), 'config.json')


def config_exists():
    return os.path.exists(get_config_path())


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                cfg.update(data)
        except Exception as e:
            print(f"讀取 config.json 失敗: {e}")
    return cfg


def save_config(cfg):
    path = get_config_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True, "已儲存設定"
    except Exception as e:
        print(f"寫入 config.json 失敗: {e}")
        return False, str(e)
