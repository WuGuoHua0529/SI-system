import json
import os

SETTINGS_FILE = 'settings.json'

class SettingsStore:
    def __init__(self):
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            self.settings = {}
            return
        
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        except Exception:
            self.settings = {}

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()
