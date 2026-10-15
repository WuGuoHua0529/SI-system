import json
import os
import tempfile
import bcrypt

from core.config import load_config, get_app_dir

DEFAULT_ADMIN = "admin"
DEFAULT_PASSWORD = "0000"


def _hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _verify(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


class AuthStore:
    """帳號名單。設定了 nas_folder 就存 NAS（所有電腦共用），否則存本機。"""

    def __init__(self, users_file=None):
        if users_file:
            self.path = users_file
        else:
            nas = load_config().get("nas_folder", "").strip()
            base = nas if nas else get_app_dir()
            self.path = os.path.join(base, 'users.json')
        self.users = {}
        try:
            self.load()
        except Exception as e:
            print(f"初始讀取帳號檔失敗: {e}")

    # ---------- 讀寫 ----------
    def load(self):
        existed = os.path.exists(self.path)
        if existed:
            # 讀取失敗（例如 NAS 瞬間斷線）必須直接報錯，
            # 不能當成「沒有帳號」，否則會用預設 admin 覆蓋掉 NAS 上整份名單
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.users = data if isinstance(data, dict) else {}
        else:
            self.users = {}
        # 檔案不存在（第一次部署）→ 建立預設 admin
        if not existed and not self.users:
            self.users[DEFAULT_ADMIN] = self._new_user(DEFAULT_PASSWORD, "admin")
            self.save()

    def save(self):
        """先寫暫存檔再替換，避免寫到一半損毀"""
        folder = os.path.dirname(self.path) or '.'
        fd, tmp = tempfile.mkstemp(dir=folder, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    @staticmethod
    def _new_user(password, role, allowed_domain=""):
        return {
            "password_hash": _hash(password),
            "raw_password": password,
            "role": role,
            "allowed_domain": allowed_domain.strip().upper(),
        }

    # ---------- 登入 ----------
    def login(self, username, password):
        """回傳 (成功?, 訊息, 角色)"""
        try:
            self.load()  # 每次登入都讀最新名單（NAS 上可能剛被管理員修改）
        except Exception:
            return False, "無法讀取帳號名單，請確認已連接公司網路 (NAS)", None
        username = username.strip()
        user = self.users.get(username)
        if not user:
            return False, "帳號或密碼錯誤", None

        if _verify(password, user["password_hash"]):
            # 帳號若有指定網域，電腦的 Windows 網域必須相符（管理員不受限，避免把自己鎖在外面）
            domain = user.get("allowed_domain", "")
            if domain and user["role"] != "admin":
                current = os.environ.get('USERDOMAIN', '').upper()
                if current != domain:
                    return False, f"此帳號限定於網域 {domain} 的電腦登入", None
            return True, "", user["role"]

        return False, "帳號或密碼錯誤", None

    # ---------- 管理 ----------
    def list_users(self):
        return [(name, u.get("raw_password", "••••"), u["role"], u.get("allowed_domain", ""))
                for name, u in sorted(self.users.items())]

    def add_user(self, username, password, allowed_domain=""):
        """新增員工帳號（一律為一般人員，只有 admin 帳號是管理員）"""
        username = username.strip()
        if not username or not password:
            return False, "帳號與密碼不可為空"
        self.load()
        if username in self.users:
            return False, "此帳號已存在"
        self.users[username] = self._new_user(password, "user", allowed_domain)
        self.save()
        return True, "已新增"

    def set_password(self, username, new_password):
        if not new_password:
            return False, "密碼不可為空"
        self.load()
        if username not in self.users:
            return False, "帳號不存在"
        self.users[username]["password_hash"] = _hash(new_password)
        self.users[username]["raw_password"] = new_password
        self.save()
        return True, "已更新密碼"

    def delete_user(self, username):
        self.load()
        if username not in self.users:
            return False, "帳號不存在"
        if self.users[username]["role"] == "admin":
            return False, "管理員帳號不能刪除"
        del self.users[username]
        self.save()
        return True, "已刪除"

    def set_domain(self, username, allowed_domain):
        self.load()
        if username not in self.users:
            return False, "帳號不存在"
        self.users[username]["allowed_domain"] = allowed_domain.strip().upper()
        self.save()
        return True, "已更新網域限制"

    def is_default_password(self, username):
        user = self.users.get(username)
        return bool(user) and _verify(DEFAULT_PASSWORD, user["password_hash"])
