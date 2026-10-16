import os
os.environ['TK_SILENCE_DEPRECATION'] = '1'
import customtkinter as ctk
import tkinter.messagebox as messagebox
import sys
import threading
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
from customtkinter import filedialog
from core.store import RulesStore
from core.settings import SettingsStore
from core.auth import AuthStore
from core.config import load_config, save_config, config_exists
from core.lan_check import check_lan
from core.excel_importer import import_excel_rules
from core.excel_exporter import export_excel_rules
from core.date_utils import normalize_date
from ui.components.data_table import DataTable
from scrapers.ista_scraper import check_ista_updates
from scrapers.ansi_scraper import check_ansi_updates
from scrapers.astm_scraper import check_astm_updates
from scrapers.din_scraper import check_din_updates
from scrapers.etsi_scraper import check_etsi_updates
from scrapers.dnv_scraper import check_dnv_updates
from scrapers.en_scraper import check_en_updates
from scrapers.iso_scraper import check_iso_updates
from scrapers.iec_scraper import check_iec_updates
from scrapers.jedec_scraper import check_jedec_updates
from scrapers.jis_scraper import check_jis_updates
from scrapers.mil_scraper import check_mil_updates
from scrapers.rtca_scraper import check_rtca_updates
from scrapers.sae_scraper import check_sae_updates
from scrapers.telcordia_scraper import check_telcordia_updates
from scrapers.un_scraper import check_un_updates
from core.teams import send_teams_notification
from urllib.parse import urlparse, urlunparse
from datetime import datetime
import time
import tkinter as tk

STANDARD_SOURCES = [
    "IEC", "ISTA", "ANSI", "ASTM", "DNV", "DIN", "ETSI", "EN",
    "ISO", "JEDEC", "JIS", "MIL", "RTCA", "SAE", "Telcordia", "UN"
]

# Basic CTk Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("規範自動查檢系統 V1.0")
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # MacOS 原生處理：綁定 Dock 點擊事件，點擊 Dock 圖示時恢復視窗
        try:
            self.createcommand("::tk::mac::ReopenApplication", self.show_window)
        except Exception:
            pass
            
        self._set_app_icon()
            
    def _set_app_icon(self):
        """設定應用程式圖示 (Mac Dock / Windows 工作列)"""
        try:
            import os
            from PIL import Image, ImageTk
            icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'app_icon.png')
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, photo)
                self._app_icon_photo = photo  # 避免被 GC 回收
        except Exception as e:
            print(f"Failed to set app icon: {e}")
            
        self._check_tray_events()
        self.setup_tray_icon()
        
        # 綁定 Mac 的 cmd+Q
        try:
            self.createcommand("::tk::mac::Quit", self.quit_app)
        except:
            pass
        
        # 依要求：預設改為全螢幕(最大化)，但允許使用者自行調整視窗大小
        self.geometry("1400x800")
        self.state('zoomed')
        self.resizable(True, True)
        
        # 啟動時先顯示 loading 蓋板
        self._show_splash()
        self.after(100, self._init_app)

    def _check_tray_events(self):
        import platform
        if platform.system() == "Windows":
            if getattr(self, '_show_requested', False):
                self._show_requested = False
                self.deiconify()
            self.after(200, self._check_tray_events)

    def _get_tray_image(self):
        try:
            import os
            from PIL import Image
            icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'tray_icon.png')
            if os.path.exists(icon_path):
                return Image.open(icon_path)
        except Exception:
            pass
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (64, 64), color=(59, 130, 246))
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
        return image

    def set_app_badge(self, active):
        if getattr(self, '_is_batch_updating', False):
            return
        import platform
        if platform.system() == "Windows":
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    if not hasattr(self, '_tray_img_normal'):
                        import os
                        from PIL import Image
                        self._tray_img_normal = Image.open(os.path.join(os.path.dirname(__file__), 'assets', 'tray_icon.png'))
                        self._tray_img_alert = Image.open(os.path.join(os.path.dirname(__file__), 'assets', 'tray_icon_alert.png'))
                    self.tray_icon.icon = self._tray_img_alert if active else self._tray_img_normal
                except Exception as e:
                    print(e)
        elif platform.system() == "Darwin":
            try:
                import AppKit
                if active:
                    AppKit.NSApp.dockTile().setBadgeLabel_("1")
                else:
                    AppKit.NSApp.dockTile().setBadgeLabel_(None)
            except:
                pass
        elif platform.system() == "Darwin":
            try:
                import AppKit
                if active:
                    AppKit.NSApp.dockTile().setBadgeLabel_("1")
                else:
                    AppKit.NSApp.dockTile().setBadgeLabel_(None)
            except:
                pass


    def setup_tray_icon(self):
        import platform
        if platform.system() == "Windows":
            menu = (
                item('開啟', self.on_tray_show, default=True),
                item('結束應用程式', self.on_tray_quit)
            )
            self.tray_icon = pystray.Icon("SIS", self._get_tray_image(), "規範自動查檢系統 V1.0", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        else:
            # Mac 版不使用上方選單小圖示，完全依賴 Mac Dock
            pass

    def on_tray_show(self, icon, item):
        self._show_requested = True

    def on_tray_quit(self, icon, item):
        icon.stop()
        self.quit_app()

    def quit_app(self):
        import os
        os._exit(0)

    def hide_window(self):
        """隱藏視窗 (類似 LINE 的運作方式，關閉視窗但不結束程式)"""
        self.withdraw()

    def show_window(self, *args):
        """從 Dock 喚醒時恢復視窗"""
        self.deiconify()

    def _show_splash(self, title="加載中...", subtitle=""):
        """在應用程式視窗上建立覆蓋式 Loading 畫面"""
        self.splash_overlay = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0)
        self.splash_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.splash_overlay.lift()
        
        # 內容置中容器
        center = ctk.CTkFrame(self.splash_overlay, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(
            center,
            text=title,
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="white"
        ).pack(pady=(0, 8))
        
        if subtitle:
            ctk.CTkLabel(
                center,
                text=subtitle,
                font=ctk.CTkFont(size=15),
                text_color="#6b7280"
            ).pack(pady=(0, 40))
        else:
            # 填補無 subtitle 時的空隙
            ctk.CTkFrame(center, height=20, fg_color="transparent").pack(pady=(0, 20))
        
        # 確定式進度條（綠色，與系統主色一致）
        self.splash_progress = ctk.CTkProgressBar(
            center,
            width=300,
            height=6,
            corner_radius=3,
            progress_color="#10b981",
            fg_color="#2d2d2d"
        )
        self.splash_progress.set(0)
        self.splash_progress.pack(pady=(0, 12))
        
        self.splash_status = ctk.CTkLabel(
            center,
            text="初始化中...",
            font=ctk.CTkFont(size=13),
            text_color="#6b7280"
        )
        self.splash_status.pack()
        
        self.update()

    def _update_splash_status(self, text, progress=None):
        """更新 Splash 上的狀態文字與進度，並確保蓋板永遠保持在最上層"""
        if hasattr(self, 'splash_status') and self.splash_status.winfo_exists():
            self.splash_status.configure(text=text)
        if progress is not None and hasattr(self, 'splash_progress') and self.splash_progress.winfo_exists():
            self.splash_progress.set(progress)
            
        # 關鍵：每次更新時都強制把蓋板拉到最上層，避免背景新建的表格穿透顯示出來
        if hasattr(self, 'splash_overlay') and self.splash_overlay.winfo_exists():
            self.splash_overlay.lift()
            
        self.update()

    def _init_app(self):
        """初始化主體 UI（在 splash overlay 下方建立）"""
        self._update_splash_status("載入資料庫...", progress=0.05)
        self.store = RulesStore()
        self.settings = SettingsStore()
        self.auth = AuthStore()
        self.current_user = ""
        self.current_role = "user"
        
        # 啟動時自動進行一次全域的日期格式修復 (套用最新版 date_utils 修正之前存留的錯字或缺空白)
        changed = False
        from core.date_utils import normalize_date
        for r in self.store.rules:
            old_p = r.get("previousDocumentName", "")
            old_l = r.get("latestDocumentName", "")
            new_p = normalize_date(old_p) if old_p else old_p
            new_l = normalize_date(old_l) if old_l else old_l
            
            if not new_l and new_p:
                new_l = new_p
            elif not new_p and new_l:
                new_p = new_l

            if old_p != new_p or old_l != new_l:
                r["previousDocumentName"] = new_p
                r["latestDocumentName"] = new_l
                changed = True
        
        if changed:
            self.store.save_rules()

        self._update_splash_status("建立介面框架...", progress=0.1)

        # Main Frame
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        # 主畫面內容容器
        self.work_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.work_frame.pack(fill="both", expand=True)

        # 標題列：左側標題、右側齒輪（僅 Admin 登入後顯示）
        self.header_frame = ctk.CTkFrame(self.work_frame, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", padx=20, pady=(20, 6))

        self.title_label = ctk.CTkLabel(self.header_frame, text="規範自動查檢系統 V1.0", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left")

        self.btn_settings = ctk.CTkButton(
            self.header_frame, text="⚙", width=40, height=36,
            font=ctk.CTkFont(size=22), fg_color="transparent", hover_color="#374151",
            text_color="#9ca3af", command=self._open_settings_window
        )

        # 標題下方的功能列：左側 Excel，右側 時間設定 / 清除 / 更新
        self.toolbar_frame = ctk.CTkFrame(self.work_frame, fg_color="transparent")
        self.toolbar_frame.pack(side="top", fill="x", padx=20, pady=(0, 10))

        self.btn_import_excel = ctk.CTkButton(self.toolbar_frame, text="匯入 Excel", fg_color="#10b981", hover_color="#059669", command=self.import_excel)
        self.btn_import_excel.pack(side="left", padx=(0, 8))

        self.btn_export_excel = ctk.CTkButton(self.toolbar_frame, text="匯出 Excel", fg_color="#0284c7", hover_color="#0369a1", command=self.export_excel)
        self.btn_export_excel.pack(side="left", padx=(0, 8))

        self.btn_update_all = ctk.CTkButton(self.toolbar_frame, text="更新全部追蹤", command=self.check_all_updates)
        self.btn_update_all.pack(side="right", padx=(8, 0))

        self.btn_clear_all = ctk.CTkButton(self.toolbar_frame, text="清除所有追蹤", fg_color="#b91c1c", hover_color="#991b1b", command=self.clear_all_data)
        self.btn_clear_all.pack(side="right", padx=(8, 0))



        # Tab Menu
        self.tab_menu_frame = ctk.CTkScrollableFrame(self.work_frame, orientation="horizontal", height=45, fg_color="transparent")
        self.tab_menu_frame.pack(side="top", fill="x", padx=20, pady=(0, 5))
        
        self.tabs = {}
        self.tab_buttons = {}
        self.active_tab = None
        self.tab_col = 0
        self.tab_row = 0
        
        # Tab Content Area
        self.tab_content_area = ctk.CTkFrame(self.work_frame, fg_color="transparent")
        self.tab_content_area.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 設定要初始化的分頁佇列
        self._tabs_to_init = list(STANDARD_SOURCES)
        self._total_tabs = len(self._tabs_to_init)
        
        # 啟動非阻塞式的非同步載入
        self.after(20, self._load_next_tab)

    def _load_next_tab(self):
        """一次只載入一個分頁，讓 Tkinter 有時間渲染畫面與進度條"""
        if self._tabs_to_init:
            tab_name = self._tabs_to_init.pop(0)
            idx = self._total_tabs - len(self._tabs_to_init)
            
            progress = 0.1 + 0.8 * (idx / self._total_tabs)
            self._update_splash_status(f"載入 {tab_name}...", progress=progress)
            
            self.add_tab(tab_name)
            
            # 排程載入下一個 (間隔 10ms，讓 UI 有空檔更新)
            self.after(10, self._load_next_tab)
        else:
            # 全部分頁都建立完成了，進行最後收尾
            self._finish_init()

    def _finish_init(self):
        # API Debug 區域
        self.debug_frame = ctk.CTkFrame(self.work_frame, fg_color="transparent")
        self.debug_btn = ctk.CTkButton(self.debug_frame, text="▶ 展開 API 除錯資訊", command=self.toggle_debug)
        self.debug_btn.pack(anchor="w")
        self.debug_text = ctk.CTkTextbox(self.debug_frame, width=800, height=250)
        self.debug_text.insert("0.0", "系統準備就緒...\n")
        
        # 載入已儲存的自訂分頁
        saved_custom_tabs = self.settings.get("custom_tabs", [])
        valid_custom_tabs = []
        for ctab in saved_custom_tabs:
            if isinstance(ctab, str) and ctab.strip() and ctab not in STANDARD_SOURCES and ctab not in valid_custom_tabs:
                valid_custom_tabs.append(ctab.strip())
                self.add_custom_tab(ctab.strip(), save_to_settings=False)
        self.settings.set("custom_tabs", valid_custom_tabs)
        self._update_add_tab_button()

        self._update_splash_status("即將完成...", progress=0.95)
        self.select_tab("IEC")
        self.refresh_tables()
        
        # 強制 Tkinter 在背景把所有的排版、表格內容都計算與繪製完畢
        self.update_idletasks()
        
        # 進度跑到 100% 後，短暫停留 300ms 讓使用者看見「完成」狀態，隨後展示登入/歡迎畫面
        self._update_splash_status("完成！", progress=1.0)
        if not config_exists():
            self.after(300, self._prompt_first_run_nas_config)
        else:
            self.after(300, self._show_login_screen)

    def _prompt_first_run_nas_config(self):
        """首次開啟應用程式（未偵測到 config.json）時彈出引導對話框"""
        dlg = ctk.CTkToplevel(self)
        dlg.title("首次開啟設定 - 公司 NAS 路徑")
        dlg.geometry("540x330")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        # 視窗置中
        try:
            dlg.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() - 540) // 2
            y = self.winfo_y() + (self.winfo_height() - 330) // 2
            dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        ctk.CTkLabel(
            dlg,
            text="首次使用設定",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff"
        ).pack(pady=(22, 8))

        ctk.CTkLabel(
            dlg,
            text="系統偵測到尚未建立連線設定檔 (config.json)。\n若您有公司的 NAS 集中帳號共用路徑，請於下方輸入或貼上；\n若暫無路徑或想先單機試用，可點選「稍後設定」。",
            font=ctk.CTkFont(size=13),
            text_color="#9ca3af",
            justify="center"
        ).pack(padx=30, pady=(0, 16))

        entry = ctk.CTkEntry(
            dlg,
            placeholder_text=r"例如: \\192.168.1.100\shared\SIS 或 Z:\SIS",
            width=430,
            height=38
        )
        entry.pack(pady=(0, 4))
        entry.focus_set()

        err_label = ctk.CTkLabel(
            dlg,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#ef4444"
        )
        err_label.pack(pady=(0, 10))

        def on_confirm():
            path_val = entry.get().strip()
            if not path_val:
                err_label.configure(text="⚠ 請輸入 NAS 路徑，或點選「稍後設定」進入單機模式")
                entry.focus_set()
                return

            err_label.configure(text="")
            status = check_lan(path_val)
            if status == 'failed':
                if not messagebox.askyesno(
                    "連線提示",
                    f"目前系統似乎無法連線至此路徑：\n{path_val}\n\n(可能尚未連上公司網路，或路徑尚未建立)\n\n確定仍要儲存此路徑嗎？",
                    parent=dlg
                ):
                    return
            save_config({"nas_folder": path_val})
            self.auth = AuthStore()
            dlg.destroy()
            self._show_login_screen()

        def on_skip():
            save_config({"nas_folder": ""})
            self.auth = AuthStore()
            dlg.destroy()
            self._show_login_screen()

        btn_box = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_box.pack(pady=(0, 10))

        ctk.CTkButton(
            btn_box,
            text="稍後設定",
            width=135,
            height=36,
            fg_color="#52525b",
            hover_color="#3f3f46",
            command=on_skip
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_box,
            text="確定儲存",
            width=135,
            height=36,
            fg_color="#10b981",
            hover_color="#059669",
            command=on_confirm
        ).pack(side="left", padx=10)

        entry.bind("<Key>", lambda e: err_label.configure(text=""))
        entry.bind("<Return>", lambda e: on_confirm())
        dlg.protocol("WM_DELETE_WINDOW", on_skip)

    def _show_login_screen(self):
        """展示登入畫面：上方【系統資訊】圓角框、下方【登入】圓角框"""
        if not hasattr(self, 'splash_overlay') or not self.splash_overlay.winfo_exists():
            self._start_auto_update_loop()
            return

        for child in self.splash_overlay.winfo_children():
            child.destroy()

        self.splash_overlay.lift()

        # 置中容器（透明），裡面放上下兩個圓角框
        wrapper = ctk.CTkFrame(self.splash_overlay, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        def make_box(title_text):
            box = ctk.CTkFrame(
                wrapper,
                corner_radius=16,
                fg_color="#242424",
                border_width=1,
                border_color="#374151",
                width=520
            )
            box.pack(fill="x", pady=8)
            return box

        # ===== 上方圓角框：系統資訊 =====
        info_box = make_box("系統資訊")

        ctk.CTkLabel(
            info_box,
            text="規範自動查檢系統 V1.0",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ffffff"
        ).pack(padx=40, pady=(28, 16))

        content_box = ctk.CTkFrame(info_box, fg_color="transparent")
        content_box.pack(padx=30, pady=(0, 24), fill="x")

        # 版次說明
        v_box = ctk.CTkFrame(content_box, corner_radius=10, fg_color="#1c1c1c", border_width=1, border_color="#333333")
        v_box.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            v_box,
            text="【 版次說明 】",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#10b981",
            anchor="w"
        ).pack(fill="x", padx=16, pady=(12, 4))

        self.lbl_version_info = ctk.CTkLabel(
            v_box,
            text="• 當前版本：V1.0 正式版\n• 系統功能：支援多國規範自動查檢、背景定時巡檢與資料匯入匯出",
            font=ctk.CTkFont(size=13),
            text_color="#9ca3af",
            justify="left",
            anchor="w"
        )
        self.lbl_version_info.pack(fill="x", padx=16, pady=(0, 14))

        # 開發者資訊
        d_box = ctk.CTkFrame(content_box, corner_radius=10, fg_color="#1c1c1c", border_width=1, border_color="#333333")
        d_box.pack(fill="x")

        ctk.CTkLabel(
            d_box,
            text="【 開發者資訊 】",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8",
            anchor="w"
        ).pack(fill="x", padx=16, pady=(12, 4))

        self.lbl_developer_info = ctk.CTkLabel(
            d_box,
            text="• 開發人員：(尚未填寫，後續補充)",
            font=ctk.CTkFont(size=13),
            text_color="#9ca3af",
            justify="left",
            anchor="w"
        )
        self.lbl_developer_info.pack(fill="x", padx=16, pady=(0, 14))

        # ===== 下方圓角框：登入 =====
        login_box = make_box("登入")

        ctk.CTkLabel(
            login_box,
            text="使用者登入",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        ).pack(pady=(24, 14))

        form = ctk.CTkFrame(login_box, fg_color="transparent")
        form.pack(padx=40)

        ctk.CTkLabel(form, text="帳號", font=ctk.CTkFont(size=13), text_color="#9ca3af", anchor="w").pack(fill="x", pady=(0, 3))
        user_entry = ctk.CTkEntry(form, placeholder_text="請輸入帳號", width=260, height=38)
        user_entry.pack(pady=(0, 10))

        ctk.CTkLabel(form, text="密碼", font=ctk.CTkFont(size=13), text_color="#9ca3af", anchor="w").pack(fill="x", pady=(0, 3))
        pw_entry = ctk.CTkEntry(form, placeholder_text="請輸入密碼", show="*", width=260, height=38)
        pw_entry.pack(pady=(0, 6))

        err_label = ctk.CTkLabel(form, text="", text_color="#ef4444", font=ctk.CTkFont(size=12), wraplength=260)
        err_label.pack()

        def do_login(event=None):
            ok, msg, role = self.auth.login(user_entry.get(), pw_entry.get())
            if not ok:
                err_label.configure(text=msg)
                pw_entry.delete(0, "end")
                return
            self.current_user = user_entry.get().strip()
            self.current_role = role
            self._apply_role_permissions()
            self._dismiss_splash()

        pw_entry.bind("<Return>", do_login)
        user_entry.bind("<Return>", lambda e: pw_entry.focus_set())

        ctk.CTkButton(
            login_box,
            text="登入",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=42,
            width=260,
            fg_color="#10b981",
            hover_color="#059669",
            corner_radius=8,
            command=do_login
        ).pack(padx=40, pady=(10, 26))
        user_entry.focus_set()

    def _apply_role_permissions(self):
        """普通帳號與管理員皆可在右上角看到設定齒輪；在設定畫面內依權限開放分頁"""
        self.btn_settings.pack(side="right")

    def _open_settings_window(self):
        """齒輪：在同一個視窗內切換到系統設定畫面（管理員具備完整權限；普通帳號只顯示時間設定與登出）"""
        if getattr(self, "settings_page", None) is not None:
            self.settings_page.destroy()
            self.settings_page = None

        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 6))
        ctk.CTkButton(
            top, text="← 返回", width=80, fg_color="#52525b", hover_color="#3f3f46",
            command=self._close_settings_page
        ).pack(side="left")
        ctk.CTkLabel(top, text="系統設定", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=16)

        # 最右邊登出圖示按鈕
        btn_logout = ctk.CTkButton(
            top, text="⎋ 登出", font=ctk.CTkFont(size=14, weight="bold"),
            width=80, height=34, fg_color="#b91c1c", hover_color="#991b1b",
            command=self._logout
        )
        btn_logout.pack(side="right")
        
        # 使用 CTkTabview 分頁
        tabview = ctk.CTkTabview(page)
        tabview.pack(fill="both", expand=True, padx=20, pady=(6, 20))

        if self.current_role == "admin":
            tabview.add("帳號管理")
            tabview.add("更改密碼")
            tabview.add("自動更新時間")
            tabview.add("Teams 通知")
            tabview.add("NAS 路徑設定")
            
            self._build_account_tab(tabview.tab("帳號管理"))
            self._build_password_tab(tabview.tab("更改密碼"))
            self._build_time_tab(tabview.tab("自動更新時間"))
            self._build_teams_tab(tabview.tab("Teams 通知"))
            self._build_nas_tab(tabview.tab("NAS 路徑設定"))
        else:
            # 普通使用者：顯示「自動更新時間」、「NAS 路徑設定」分頁和頂部「登出」按鈕
            tabview.add("自動更新時間")
            tabview.add("NAS 路徑設定")
            self._build_time_tab(tabview.tab("自動更新時間"))
            self._build_nas_tab(tabview.tab("NAS 路徑設定"))
            
        self.settings_page = page
        self.work_frame.pack_forget()
        self.settings_page.pack(fill="both", expand=True)

    def _close_settings_page(self):
        self.settings_page.pack_forget()
        self.work_frame.pack(fill="both", expand=True)

    def _logout(self):
        """登出當前使用者並返回登入畫面"""
        if messagebox.askyesno("登出確認", "確定要登出並返回登入畫面嗎？"):
            # 銷毀設定頁與隱藏工作頁
            if getattr(self, "settings_page", None) is not None:
                self.settings_page.destroy()
                self.settings_page = None
            if getattr(self, "work_frame", None) is not None:
                self.work_frame.pack_forget()
            if getattr(self, "btn_settings", None) is not None:
                self.btn_settings.pack_forget()
            
            # 清除當前使用者狀態
            self.current_user = ""
            self.current_role = "user"
            
            # 重新建立覆蓋層並展示登入畫面
            if not hasattr(self, 'splash_overlay') or not self.splash_overlay.winfo_exists():
                self.splash_overlay = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0)
                self.splash_overlay.place(x=0, y=0, relwidth=1, relheight=1)
            self._show_login_screen()

    def _build_account_tab(self, parent):
        """帳號管理：透過彈窗新增員工帳號，並提供即時更新的清單列表管理"""
        # 1. 頂部操作列：標題 + 「＋ 新增員工帳號」彈窗觸發按鈕
        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(top_bar, text="【 帳號清單管理 】", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        count_lbl = ctk.CTkLabel(top_bar, text="共 0 個帳號", text_color="#9ca3af")
        count_lbl.pack(side="left", padx=10)

        def open_add_user_dialog():
            dlg = ctk.CTkToplevel(self)
            dlg.title("新增員工帳號")
            dlg.geometry("420x360")
            dlg.transient(self)
            dlg.grab_set()
            dlg.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() - 420) // 2
            y = self.winfo_y() + (self.winfo_height() - 360) // 2
            dlg.geometry(f"+{x}+{y}")

            ctk.CTkLabel(dlg, text="新增員工帳號", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 16))

            form = ctk.CTkFrame(dlg, fg_color="transparent")
            form.pack(padx=35, fill="x")

            ctk.CTkLabel(form, text="員工帳號：", anchor="w", font=("Helvetica", 13)).pack(fill="x", pady=(4, 2))
            entry_user = ctk.CTkEntry(form, placeholder_text="例如: john_doe", height=35)
            entry_user.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(form, text="預設密碼：", anchor="w", font=("Helvetica", 13)).pack(fill="x", pady=(4, 2))
            entry_pw = ctk.CTkEntry(form, placeholder_text="請設定登入密碼", show="*", height=35)
            entry_pw.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(form, text="限定網域 (選填)：", anchor="w", font=("Helvetica", 13)).pack(fill="x", pady=(4, 2))
            entry_domain = ctk.CTkEntry(form, placeholder_text="例如: IST (留白＝不限制)", height=35)
            entry_domain.pack(fill="x", pady=(0, 16))

            def on_confirm():
                u = entry_user.get().strip()
                p = entry_pw.get().strip()
                d = entry_domain.get().strip()
                if not u or not p:
                    messagebox.showwarning("提示", "帳號與密碼皆不可為空！", parent=dlg)
                    return
                ok, msg = self.auth.add_user(u, p, d)
                if ok:
                    messagebox.showinfo("成功", f"員工帳號 [{u}] 已成功建立！", parent=dlg)
                    dlg.destroy()
                    refresh_list()
                else:
                    messagebox.showwarning("提示", msg, parent=dlg)

            btn_box = ctk.CTkFrame(dlg, fg_color="transparent")
            btn_box.pack(pady=(8, 15))

            ctk.CTkButton(btn_box, text="取消", width=90, fg_color="#52525b", hover_color="#3f3f46", command=dlg.destroy).pack(side="left", padx=10)
            ctk.CTkButton(btn_box, text="確認新增", width=110, fg_color="#10b981", hover_color="#059669", command=on_confirm).pack(side="left", padx=10)

            entry_user.focus_set()
            dlg.bind("<Escape>", lambda e: dlg.destroy())

        ctk.CTkButton(top_bar, text="＋ 新增員工帳號", font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color="#10b981", hover_color="#059669", height=32,
                      command=open_add_user_dialog).pack(side="right")

        # 2. 下半部：現有帳號清單列表卡片
        list_card = ctk.CTkFrame(parent, fg_color="#242424", corner_radius=10)
        list_card.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # 列表表頭
        header_row = ctk.CTkFrame(list_card, height=32, fg_color="#343638", corner_radius=4)
        header_row.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(header_row, text="帳號名稱", width=140, font=("Helvetica", 12, "bold"), anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(header_row, text="密碼", width=130, font=("Helvetica", 12, "bold"), anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(header_row, text="身分角色", width=110, font=("Helvetica", 12, "bold"), anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(header_row, text="限定網域", width=140, font=("Helvetica", 12, "bold"), anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(header_row, text="操作", font=("Helvetica", 12, "bold"), anchor="e").pack(side="right", padx=16)

        scroll_area = ctk.CTkScrollableFrame(list_card, fg_color="transparent")
        scroll_area.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        def refresh_list():
            self.auth.load()
            for w in scroll_area.winfo_children():
                w.destroy()
            users = self.auth.list_users()
            count_lbl.configure(text=f"共 {len(users)} 個帳號")

            for idx, (name, raw_pw, role, domain) in enumerate(users):
                bg = "#2b2b2b" if idx % 2 == 0 else "#242424"
                row = ctk.CTkFrame(scroll_area, fg_color=bg, height=44, corner_radius=4)
                row.pack(fill="x", pady=2)

                # 帳號名稱
                ctk.CTkLabel(row, text=name, width=140, anchor="w", font=("Helvetica", 13, "bold" if role=="admin" else "normal")).pack(side="left", padx=10)

                # 密碼列出在管理表內
                pw_show = raw_pw if raw_pw else "••••"
                ctk.CTkLabel(row, text=pw_show, width=130, anchor="w", text_color="#fcd34d", font=("Courier", 13, "bold")).pack(side="left", padx=8)

                # 角色
                role_text = "系統管理員" if role == "admin" else "一般人員"
                role_color = "#38bdf8" if role == "admin" else "#9ca3af"
                ctk.CTkLabel(row, text=role_text, width=110, text_color=role_color, anchor="w").pack(side="left", padx=8)

                # 網域
                dom_text = domain if domain else "(不限網域)"
                ctk.CTkLabel(row, text=dom_text, width=140, text_color="#cbd5e1" if domain else "#64748b", anchor="w").pack(side="left", padx=8)

                # 操作按鈕群 (改密碼、改網域、刪除)
                if role != "admin":
                    ctk.CTkButton(row, text="刪除", width=50, height=26, fg_color="#b91c1c", hover_color="#991b1b",
                                  command=lambda n=name: do_delete(n)).pack(side="right", padx=(4, 10))
                    ctk.CTkButton(row, text="改網域", width=55, height=26, fg_color="#475569", hover_color="#334155",
                                  command=lambda n=name: do_domain(n)).pack(side="right", padx=4)
                    ctk.CTkButton(row, text="改密碼", width=55, height=26, fg_color="#2563eb", hover_color="#1d4ed8",
                                  command=lambda n=name: do_edit_password(n)).pack(side="right", padx=4)

        def do_delete(name):
            if name == self.current_user:
                messagebox.showwarning("提示", "不能刪除目前登入中的帳號！")
                return
            if messagebox.askyesno("刪除確認", f"確定要刪除員工帳號 [{name}] 嗎？\n刪除後該人員將無法登入系統。"):
                ok, msg = self.auth.delete_user(name)
                if not ok:
                    messagebox.showwarning("提示", msg)
                refresh_list()

        def do_domain(name):
            dlg = ctk.CTkInputDialog(text=f"請輸入 [{name}] 允許登入的 Windows 網域：\n(若留白則表示不限制網域)", title="修改限定網域")
            val = dlg.get_input()
            if val is not None:
                ok, msg = self.auth.set_domain(name, val)
                messagebox.showinfo("結果", msg)
                refresh_list()

        def do_edit_password(name):
            dlg = ctk.CTkInputDialog(text=f"請輸入 [{name}] 的新密碼：", title="修改員工密碼")
            val = dlg.get_input()
            if val is not None:
                new_p = val.strip()
                if not new_p:
                    messagebox.showwarning("提示", "密碼不可為空！")
                    return
                ok, msg = self.auth.set_password(name, new_p)
                messagebox.showinfo("結果", f"帳號 [{name}] 密碼已更新！")
                refresh_list()

        refresh_list()
        self._refresh_account_list = refresh_list

    def _build_password_tab(self, parent):
        """更改密碼：專屬於管理者 (admin) 修改自身登入密碼"""
        card = ctk.CTkFrame(parent, fg_color="#242424", corner_radius=10)
        card.pack(fill="x", padx=40, pady=25)

        ctk.CTkLabel(card, text="【 管理者密碼變更 】", font=ctk.CTkFont(size=16, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=20, pady=(16, 8))

        form_box = ctk.CTkFrame(card, fg_color="transparent")
        form_box.pack(padx=20, pady=(0, 20), fill="x")

        # 標明目前帳號
        target_admin = self.current_user if self.current_user else "admin"
        ctk.CTkLabel(form_box, text=f"管理者帳號： {target_admin}", font=("Helvetica", 14, "bold"), text_color="#10b981", anchor="w").pack(fill="x", pady=(4, 12))

        # 新密碼
        ctk.CTkLabel(form_box, text="輸入新密碼：", font=("Helvetica", 13), anchor="w").pack(fill="x", pady=(4, 2))
        new_pw_entry = ctk.CTkEntry(form_box, placeholder_text="請輸入管理員新密碼", show="*", width=280, height=36)
        new_pw_entry.pack(anchor="w", pady=(0, 10))

        # 確認新密碼
        ctk.CTkLabel(form_box, text="確認新密碼：", font=("Helvetica", 13), anchor="w").pack(fill="x", pady=(4, 2))
        confirm_pw_entry = ctk.CTkEntry(form_box, placeholder_text="請再次輸入管理員新密碼", show="*", width=280, height=36)
        confirm_pw_entry.pack(anchor="w", pady=(0, 16))

        def do_change_password():
            p1 = new_pw_entry.get().strip()
            p2 = confirm_pw_entry.get().strip()
            if not p1:
                messagebox.showerror("錯誤", "新密碼不可為空！")
                return
            if p1 != p2:
                messagebox.showerror("錯誤", "兩次輸入的新密碼不一致，請重新檢查！")
                return
            ok, msg = self.auth.set_password(target_admin, p1)
            if ok:
                new_pw_entry.delete(0, "end")
                confirm_pw_entry.delete(0, "end")
                messagebox.showinfo("成功", f"管理者帳號 [{target_admin}] 密碼已成功變更！")
            else:
                messagebox.showerror("失敗", msg)

        btn_save = ctk.CTkButton(form_box, text="確認變更管理員密碼", command=do_change_password, fg_color="#10b981", hover_color="#059669", width=200, height=38)
        btn_save.pack(anchor="w", pady=(8, 0))

    def _dismiss_splash(self):
        """移除覆蓋層，顯示已建好的主畫面"""
        if hasattr(self, 'splash_overlay') and self.splash_overlay.winfo_exists():
            self.splash_overlay.destroy()
        if hasattr(self, 'work_frame') and self.work_frame is not None:
            self.work_frame.pack(fill="both", expand=True)
        self._start_auto_update_loop()

    def _start_auto_update_loop(self):
        if getattr(self, '_auto_update_loop_running', False):
            return
        self._auto_update_loop_running = True
        self._check_auto_update()

    def _check_auto_update(self):
        target_time = self.settings.get("auto_update_time", "")
        if target_time:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")
            
            if current_time == target_time:
                last_update = self.settings.get("last_auto_update_date", "")
                if last_update != current_date:
                    self.settings.set("last_auto_update_date", current_date)
                    self.check_all_updates(is_auto=True)
        
        # 每 30 秒檢查一次
        self.after(30000, self._check_auto_update)


    def _build_time_tab(self, parent):
        current_time = self.settings.get("auto_update_time", "")
        ctk.CTkLabel(parent, text="請輸入每日自動更新時間", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(25, 10))

        input_frame = ctk.CTkFrame(parent, fg_color="transparent")
        input_frame.pack(pady=10)
        entry_h = ctk.CTkEntry(input_frame, width=60, justify="center", placeholder_text="14")
        entry_h.pack(side="left", padx=5)
        ctk.CTkLabel(input_frame, text=":", font=("Helvetica", 16, "bold")).pack(side="left")
        entry_m = ctk.CTkEntry(input_frame, width=60, justify="center", placeholder_text="30")
        entry_m.pack(side="left", padx=5)
        if current_time:
            h, m = current_time.split(":")
            entry_h.insert(0, h)
            entry_m.insert(0, m)

        def on_confirm():
            h_val = entry_h.get().strip()
            m_val = entry_m.get().strip()
            if not h_val or not m_val:
                messagebox.showerror("錯誤", "小時與分鐘皆不可為空！\n(若要取消排程，請點擊「清除設定」)")
                return
            try:
                h_int = int(h_val)
                m_int = int(m_val)
                if not (0 <= h_int <= 23 and 0 <= m_int <= 59):
                    raise ValueError
            except ValueError:
                messagebox.showerror("錯誤", "請輸入有效的時間格式\n小時: 0-23, 分鐘: 0-59")
                return
            result = f"{h_int:02d}:{m_int:02d}"
            self.settings.set("auto_update_time", result)
            self.settings.set("last_auto_update_date", "")
            messagebox.showinfo("設定成功", f"已設定每日 {result} 自動更新！")

        def on_clear():
            self.settings.set("auto_update_time", "")
            self.settings.set("last_auto_update_date", "")
            entry_h.delete(0, "end")
            entry_m.delete(0, "end")
            messagebox.showinfo("設定成功", "已清除每日自動更新。")

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="清除設定", width=80, fg_color="#b91c1c", hover_color="#991b1b", command=on_clear).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="確定", width=80, command=on_confirm).pack(side="left", padx=10)

    def _build_teams_tab(self, parent):
        """Teams 通知：設定 Microsoft Teams Incoming Webhook 進行自動更新完成通知"""
        card = ctk.CTkFrame(parent, fg_color="#242424", corner_radius=10)
        card.pack(fill="x", padx=40, pady=25)

        ctk.CTkLabel(
            card, text="【 Microsoft Teams Webhook 通知設定 】",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#38bdf8"
        ).pack(anchor="w", padx=20, pady=(16, 6))

        desc_text = (
            "說明：設定 Teams 頻道的 Incoming Webhook / Workflows 網址。\n"
            "每日排程「自動更新」完成後，系統會自動發送通知至指定 Teams 頻道：\n"
            "  • 若有更新：將整理列出各項異動清單（標明前次版本 ➔ 最新版本與法規連結）。\n"
            "  • 若無更新：亦會發送檢查報告，確認當日所有項目皆為最新版本。\n"
            "（注意：僅每日排程自動更新完成後會發送通知；手動點擊更新不會發送通知）"
        )
        ctk.CTkLabel(
            card, text=desc_text, font=("Helvetica", 12), text_color="#9ca3af", justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 16))

        form_box = ctk.CTkFrame(card, fg_color="transparent")
        form_box.pack(padx=20, pady=(0, 20), fill="x")

        # 1. 啟用開關
        switch_teams = ctk.CTkSwitch(
            form_box, text="啟用 Microsoft Teams 通知", font=("Helvetica", 14, "bold"),
            progress_color="#10b981"
        )
        switch_teams.pack(anchor="w", pady=(0, 16))
        if self.settings.get("teams_enabled", False):
            switch_teams.select()
        else:
            switch_teams.deselect()

        # 2. Webhook 網址
        ctk.CTkLabel(
            form_box, text="Webhook 網址 (Incoming Webhook / Workflows URL)：",
            font=("Helvetica", 13), anchor="w"
        ).pack(fill="x", pady=(4, 2))
        entry_url = ctk.CTkEntry(
            form_box,
            placeholder_text="https://outlook.office.com/webhook/... 或 https://...workflows.azure.com/...",
            height=36
        )
        entry_url.pack(fill="x", pady=(0, 18))
        current_url = self.settings.get("teams_webhook_url", "")
        if current_url:
            entry_url.insert(0, current_url)

        # 按鈕列
        btn_frame = ctk.CTkFrame(form_box, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(4, 0))

        def on_test():
            url = entry_url.get().strip()
            if not url:
                messagebox.showwarning("提示", "請先輸入 Teams Webhook 網址！")
                return
            if not (url.startswith("http://") or url.startswith("https://")):
                messagebox.showerror("錯誤", "Webhook 網址格式不正確，需以 http:// 或 https:// 開頭！")
                return

            btn_test.configure(state="disabled", text="發送中...")

            def _bg_test():
                ok, msg = send_teams_notification(
                    webhook_url=url,
                    title="🔔 【規範自動檢查系統】Teams Webhook 連線測試",
                    summary="這是一則來自規範自動檢查系統的測試通知。若您看見此卡片，代表 Teams Incoming Webhook 串接設定完全正確！",
                    is_test=True
                )
                def _done():
                    btn_test.configure(state="normal", text="🔔 測試發送")
                    if ok:
                        messagebox.showinfo("測試成功", "已成功發送測試卡片至 Teams 頻道！\n請至您的 Teams 頻道查看訊息。")
                    else:
                        messagebox.showerror("測試失敗", f"無法發送至 Teams：\n{msg}")
                self.after(0, _done)

            threading.Thread(target=_bg_test, daemon=True).start()

        def on_save():
            is_enabled = bool(switch_teams.get())
            url = entry_url.get().strip()

            if is_enabled and not url:
                messagebox.showwarning("提示", "已勾選啟用 Teams 通知，但尚未填寫 Webhook 網址！")
                return

            self.settings.set("teams_enabled", is_enabled)
            self.settings.set("teams_webhook_url", url)
            messagebox.showinfo("成功", "Microsoft Teams 通知設定已成功儲存！")

        btn_test = ctk.CTkButton(
            btn_frame, text="🔔 測試發送", width=120, height=36,
            fg_color="#3b82f6", hover_color="#2563eb", command=on_test
        )
        btn_test.pack(side="left", padx=(0, 12))

        btn_save = ctk.CTkButton(
            btn_frame, text="確認儲存設定", width=130, height=36,
            fg_color="#10b981", hover_color="#059669", command=on_save
        )
        btn_save.pack(side="left")

    def _build_nas_tab(self, parent):
        """NAS 路徑設定：設定公司 NAS 共用路徑 (config.json)"""
        card = ctk.CTkFrame(parent, fg_color="#242424", corner_radius=10)
        card.pack(fill="x", padx=40, pady=25)

        ctk.CTkLabel(
            card, text="【 NAS 路徑設定 】",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#38bdf8"
        ).pack(anchor="w", padx=20, pady=(16, 6))

        desc_text = "• 若未填寫 (留白)，系統將自動切換為本機單機離線模式。"
        ctk.CTkLabel(
            card, text=desc_text, font=ctk.CTkFont(size=13),
            text_color="#9ca3af", justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 16))

        form_box = ctk.CTkFrame(card, fg_color="transparent")
        form_box.pack(padx=20, pady=(0, 20), fill="x")

        cfg = load_config()
        current_nas = cfg.get("nas_folder", "")

        ctk.CTkLabel(form_box, text="路徑：", font=("Helvetica", 13), anchor="w").pack(fill="x", pady=(4, 2))
        entry_nas = ctk.CTkEntry(
            form_box,
            placeholder_text=r"例如: \\192.168.1.100\shared\SIS 或 Z:\SIS (留白＝單機模式)",
            height=38,
            width=500
        )
        entry_nas.insert(0, current_nas)
        entry_nas.pack(anchor="w", pady=(0, 10))

        lbl_status = ctk.CTkLabel(
            form_box,
            text=f"目前連線路徑：{current_nas if current_nas else '(未設定，單機離線模式)'}",
            font=("Helvetica", 12),
            text_color="#10b981" if current_nas else "#f59e0b",
            anchor="w"
        )
        lbl_status.pack(fill="x", pady=(0, 16))

        def on_save_nas():
            val = entry_nas.get().strip()
            if val:
                status = check_lan(val)
                if status == 'failed':
                    if not messagebox.askyesno(
                        "連線提示",
                        f"目前系統似乎無法連線至此路徑：\n{val}\n\n(可能尚未連上公司網路，或路徑尚未建立)\n\n確定仍要儲存此路徑嗎？"
                    ):
                        return
            ok, msg = save_config({"nas_folder": val})
            if ok:
                self.auth = AuthStore()
                lbl_status.configure(
                    text=f"目前連線路徑：{val if val else '(未設定，單機離線模式)'}",
                    text_color="#10b981" if val else "#f59e0b"
                )
                if hasattr(self, '_refresh_account_list'):
                    try:
                        self._refresh_account_list()
                    except Exception:
                        pass
                messagebox.showinfo(
                    "儲存成功",
                    f"NAS 連線設定已成功儲存並同步至 config.json！\n\n"
                    f"路徑：{val if val else '已切換為單機離線模式'}\n\n"
                    "提示：若更換了新的 NAS 帳號庫，建議稍後重新登入以載入最新使用者名單。"
                )
            else:
                messagebox.showerror("儲存失敗", f"寫入 config.json 失敗：{msg}")

        btn_save = ctk.CTkButton(
            form_box, text="儲存", width=90, height=36,
            fg_color="#10b981", hover_color="#059669", command=on_save_nas
        )
        btn_save.pack(anchor="w")

    def clear_all_data(self):
        """清除所有追蹤項目資料（保留分類本身）"""
        import tkinter.messagebox as messagebox
        if not self.store.rules:
            messagebox.showinfo("提示", "目前系統中沒有任何追蹤資料。")
            return
            
        confirm = messagebox.askyesno("警告", "這將會清除您目前在所有分類中建立的所有追蹤項目（分類分頁本身會保留）。\n\n確定要全部清除嗎？", icon='warning')
        if confirm:
            self.store.rules = []
            self.store.save_rules()
            self.refresh_tables()
            messagebox.showinfo("清除完成", "所有追蹤資料已成功清除！")

    def toggle_debug(self):
        if self.debug_text.winfo_ismapped():
            self.debug_text.pack_forget()
            self.debug_btn.configure(text="▶ 展開 API 除錯資訊")
        else:
            self.debug_text.pack(pady=(10, 0), fill="x")
            self.debug_btn.configure(text="▼ 收合 API 除錯資訊")

    def _get_tab_label(self, name):
        if name in self.settings.get("custom_tabs", []):
            return f"📁 {name}"
        return name

    def _update_single_tab_style(self, name):
        if name not in self.tab_buttons:
            return
        is_active = (self.active_tab == name)
        custom_tabs = self.settings.get("custom_tabs", [])
        is_custom = name in custom_tabs

        if is_custom:
            rules = self.store.get_rules_by_tag(name)
            has_update = any(r.get("tab_unread") for r in rules)
            tab_frame = self.tab_buttons[name]
            btn_tab = getattr(tab_frame, "btn_tab", None)
            btn_close = getattr(tab_frame, "btn_close", None)

            if is_active:
                tab_frame.configure(fg_color="#1f538d")
                if btn_tab:
                    btn_tab.configure(fg_color="#1f538d", hover_color="#1f538d", text_color="white")
                if btn_close:
                    btn_close.configure(fg_color="#1f538d", text_color="white")
            else:
                tab_frame.configure(fg_color="transparent")
                if btn_tab:
                    btn_tab.configure(fg_color="transparent", hover_color="#2b2b2b", text_color="#10b981" if has_update else "gray")
                if btn_close:
                    btn_close.configure(fg_color="transparent", text_color="#10b981" if has_update else "gray")

            if has_update:
                tab_frame.configure(border_width=2, border_color="#10b981")
            else:
                tab_frame.configure(border_width=0)

        else:
            rules = self.store.get_rules_by_source(name)
            has_update = any(r.get("tab_unread") for r in rules)
            btn = self.tab_buttons[name]

            if has_update:
                btn.configure(
                    border_width=2,
                    border_color="#10b981",
                    fg_color="#1f538d" if is_active else "transparent",
                    text_color="white" if is_active else "#10b981"
                )
            else:
                btn.configure(
                    border_width=0,
                    fg_color="#1f538d" if is_active else "transparent",
                    text_color="white" if is_active else "gray"
                )

    def _regrid_tab_buttons(self):
        col = 0
        for name, btn in self.tab_buttons.items():
            btn.grid(row=0, column=col, padx=(0, 5), pady=(0, 5))
            col += 1
        self.tab_col = col
        self._update_add_tab_button()

    def _update_add_tab_button(self):
        if hasattr(self, 'btn_add_tab') and self.btn_add_tab is not None:
            self.btn_add_tab.grid_forget()
        self.btn_add_tab = ctk.CTkButton(
            self.tab_menu_frame,
            text="＋",
            width=36,
            height=28,
            corner_radius=4,
            fg_color="#334155",
            hover_color="#475569",
            text_color="#38bdf8",
            font=("Helvetica", 14, "bold"),
            command=self._open_add_tab_dialog
        )
        self.btn_add_tab.grid(row=0, column=self.tab_col, padx=(0, 5), pady=(0, 5))

    def add_tab(self, name):
        # 建立分頁按鈕 (靠左對齊，適度縮減寬度以利單行顯示更多)
        btn = ctk.CTkButton(
            self.tab_menu_frame, 
            text=name, 
            width=75, 
            corner_radius=4,
            fg_color="transparent",
            text_color="gray",
            hover_color="#2b2b2b",
            command=lambda n=name: self.select_tab(n)
        )
        btn.grid(row=0, column=self.tab_col, padx=(0, 5), pady=(0, 5))
        self.tab_buttons[name] = btn
        
        self.tab_col += 1
        
        # 建立表格內容
        table = DataTable(
            self.tab_content_area, 
            self.store, 
            name, 
            is_custom=False,
            on_delete=self.confirm_delete,
            on_add=self.open_add_dialog,
            on_update=self.check_category_updates,
            on_row_update=self.run_single_update
        )
        self.tabs[name] = table

    def add_custom_tab(self, name, save_to_settings=True):
        if save_to_settings:
            custom_tabs = self.settings.get("custom_tabs", [])
            if name not in custom_tabs:
                custom_tabs.append(name)
                self.settings.set("custom_tabs", custom_tabs)

        tab_frame = ctk.CTkFrame(self.tab_menu_frame, fg_color="transparent", corner_radius=4)
        tab_frame.grid(row=0, column=self.tab_col, padx=(0, 5), pady=(0, 5))

        label = self._get_tab_label(name)
        btn_tab = ctk.CTkButton(
            tab_frame,
            text=label,
            width=0,
            height=28,
            corner_radius=4,
            fg_color="transparent",
            text_color="gray",
            hover_color="#2b2b2b",
            command=lambda n=name: self.select_tab(n)
        )
        btn_tab.pack(side="left", padx=(4, 0))

        btn_close = ctk.CTkButton(
            tab_frame,
            text="✕",
            width=0,
            height=28,
            corner_radius=4,
            fg_color="transparent",
            hover=False,
            text_color="gray",
            font=("Helvetica", 11),
            command=lambda n=name: self.confirm_delete_custom_tab(n)
        )
        btn_close.pack(side="left", padx=(1, 5))

        tab_frame.btn_tab = btn_tab
        tab_frame.btn_close = btn_close

        self.tab_buttons[name] = tab_frame
        self.tab_col += 1

        table = DataTable(
            self.tab_content_area,
            self.store,
            name,
            is_custom=True,
            on_delete=self.confirm_custom_tab_remove,
            on_add=self.open_custom_tab_add_dialog,
            on_update=self.check_custom_tab_updates,
            on_row_update=self.run_single_update,
            on_select_existing=self.open_select_existing_dialog
        )
        self.tabs[name] = table
        self._update_add_tab_button()

    def _open_add_tab_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("新增自訂分頁")
        dialog.geometry("500x530")
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 530) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

        # 1. 分頁名稱
        ctk.CTkLabel(dialog, text="分頁名稱:", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x", padx=25, pady=(20, 5))

        name_entry = ctk.CTkEntry(dialog, placeholder_text="請輸入自訂分頁名稱 (例如: 客戶A專案)", width=450, height=36)
        name_entry.pack(padx=25, pady=(0, 15))
        name_entry.focus_set()

        # 2. 選擇現有項目追蹤
        ctk.CTkLabel(dialog, text="選擇現有項目追蹤 (可切換類別勾選):", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x", padx=25, pady=(0, 8))

        cat_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        cat_frame.pack(fill="x", padx=25, pady=(0, 8))

        ctk.CTkLabel(cat_frame, text="選擇類別:", font=("Helvetica", 13)).pack(side="left", padx=(0, 8))

        cat_var = ctk.StringVar(value="IEC")
        cat_menu = ctk.CTkOptionMenu(cat_frame, values=STANDARD_SOURCES, variable=cat_var, width=140)
        cat_menu.pack(side="left")

        lbl_count = ctk.CTkLabel(cat_frame, text="已勾選: 0 項", text_color="#38bdf8", font=("Helvetica", 13))
        lbl_count.pack(side="right")

        # 項目列表滾動區域
        scroll_frame = ctk.CTkScrollableFrame(dialog, height=220, fg_color="#1c1c1c", corner_radius=8)
        scroll_frame.pack(fill="both", expand=True, padx=25, pady=(0, 15))

        selected_ids = set()

        def update_count():
            lbl_count.configure(text=f"已勾選: {len(selected_ids)} 項")

        def on_check_toggle(rule_id, var):
            if var.get():
                selected_ids.add(rule_id)
            else:
                selected_ids.discard(rule_id)
            update_count()

        def populate_items(cat_name):
            for w in scroll_frame.winfo_children():
                w.destroy()

            rules_in_cat = [r for r in self.store.rules if r.get("source") == cat_name]
            if not rules_in_cat:
                ctk.CTkLabel(scroll_frame, text=f"({cat_name} 目前沒有任何追蹤項目)", text_color="gray", font=("Helvetica", 13)).pack(pady=40)
                return

            for r in rules_in_cat:
                r_id = r["id"]
                var = tk.BooleanVar(value=(r_id in selected_ids))
                cb = ctk.CTkCheckBox(
                    scroll_frame,
                    text=r.get("name", ""),
                    variable=var,
                    font=("Helvetica", 13),
                    command=lambda rid=r_id, v=var: on_check_toggle(rid, v)
                )
                cb.pack(anchor="w", padx=15, pady=5)

        cat_menu.configure(command=populate_items)
        populate_items("IEC")

        # 3. 底部操作按鈕
        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(fill="x", padx=25, pady=(0, 20))

        def on_confirm(event=None):
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("錯誤", "分頁名稱不可為空！")
                return
            if name in STANDARD_SOURCES:
                messagebox.showerror("錯誤", f"分頁名稱不可與系統內建分類 [{name}] 重複！")
                return
            existing_custom = self.settings.get("custom_tabs", [])
            if name in existing_custom or name in self.tabs:
                messagebox.showerror("錯誤", f"已存在相同名稱的分頁 [{name}]！")
                return
            if len(name) > 20:
                messagebox.showerror("錯誤", "分頁名稱長度請勿超過 20 個字！")
                return

            # 建立自訂分頁
            self.add_custom_tab(name, save_to_settings=True)

            # 將已勾選的項目加入此分頁標籤
            for rid in selected_ids:
                self.store.add_tag_to_rule(rid, name)

            self.select_tab(name)
            self.refresh_tables()
            dialog.destroy()
            messagebox.showinfo("建立成功", f"自訂分頁 [{name}] 已建立！\n已納入 {len(selected_ids)} 個追蹤項目。")

        name_entry.bind("<Return>", on_confirm)

        ctk.CTkButton(btn_box, text="取消", width=90, fg_color="#475569", hover_color="#334155", command=dialog.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_box, text="確定建立", width=100, fg_color="#10b981", hover_color="#059669", command=on_confirm).pack(side="right")

    def confirm_delete_custom_tab(self, tab_name):
        confirm = messagebox.askyesno(
            "刪除自訂分頁",
            f"確定要刪除自訂分頁 [{tab_name}] 嗎？\n\n注意：這只會移除此自訂分頁標籤，所有項目的原始規範追蹤資料將完整保留！"
        )
        if confirm:
            self.store.remove_tag_from_all_rules(tab_name)
            custom_tabs = self.settings.get("custom_tabs", [])
            if tab_name in custom_tabs:
                custom_tabs.remove(tab_name)
                self.settings.set("custom_tabs", custom_tabs)

            if tab_name in self.tabs:
                self.tabs[tab_name].destroy()
                del self.tabs[tab_name]
            if tab_name in self.tab_buttons:
                self.tab_buttons[tab_name].destroy()
                del self.tab_buttons[tab_name]

            self._regrid_tab_buttons()
            self.select_tab("IEC")
            self.refresh_tables()
            messagebox.showinfo("已刪除", f"自訂分頁 [{tab_name}] 已成功刪除。")

    def confirm_custom_tab_remove(self, rule_id, tab_name):
        confirm = messagebox.askyesno("移出確認", f"確定要將此項目從自訂分頁 [{tab_name}] 移出嗎？\n\n(原始來源資料仍會保留在原分類中)")
        if confirm:
            self.store.remove_tag_from_rule(rule_id, tab_name)
            self.tabs[tab_name].refresh_table()

    def open_select_existing_dialog(self, tab_name):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"從現有項目挑選加入 [{tab_name}]")
        dialog.geometry("500x480")
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 480) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

        ctk.CTkLabel(
            dialog,
            text=f"請選擇要納入【{tab_name}】追蹤的現有項目：",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8",
            anchor="w"
        ).pack(fill="x", padx=25, pady=(20, 10))

        cat_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        cat_frame.pack(fill="x", padx=25, pady=(0, 8))

        ctk.CTkLabel(cat_frame, text="選擇類別:", font=("Helvetica", 13)).pack(side="left", padx=(0, 8))

        cat_var = ctk.StringVar(value="IEC")
        cat_menu = ctk.CTkOptionMenu(cat_frame, values=STANDARD_SOURCES, variable=cat_var, width=140)
        cat_menu.pack(side="left")

        # 初始將目前已屬於此 tab 的項目 id 放入集合
        selected_ids = {r["id"] for r in self.store.rules if tab_name in r.get("tags", [])}

        lbl_count = ctk.CTkLabel(cat_frame, text=f"已勾選: {len(selected_ids)} 項", text_color="#38bdf8", font=("Helvetica", 13))
        lbl_count.pack(side="right")

        scroll_frame = ctk.CTkScrollableFrame(dialog, height=240, fg_color="#1c1c1c", corner_radius=8)
        scroll_frame.pack(fill="both", expand=True, padx=25, pady=(0, 15))

        def update_count():
            lbl_count.configure(text=f"已勾選: {len(selected_ids)} 項")

        def on_check_toggle(rule_id, var):
            if var.get():
                selected_ids.add(rule_id)
            else:
                selected_ids.discard(rule_id)
            update_count()

        def populate_items(cat_name):
            for w in scroll_frame.winfo_children():
                w.destroy()

            rules_in_cat = [r for r in self.store.rules if r.get("source") == cat_name]
            if not rules_in_cat:
                ctk.CTkLabel(scroll_frame, text=f"({cat_name} 目前沒有任何追蹤項目)", text_color="gray", font=("Helvetica", 13)).pack(pady=40)
                return

            for r in rules_in_cat:
                r_id = r["id"]
                var = tk.BooleanVar(value=(r_id in selected_ids))
                cb = ctk.CTkCheckBox(
                    scroll_frame,
                    text=r.get("name", ""),
                    variable=var,
                    font=("Helvetica", 13),
                    command=lambda rid=r_id, v=var: on_check_toggle(rid, v)
                )
                cb.pack(anchor="w", padx=15, pady=5)

        cat_menu.configure(command=populate_items)
        populate_items("IEC")

        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(fill="x", padx=25, pady=(0, 20))

        def on_save():
            changed = False
            for r in self.store.rules:
                r_id = r["id"]
                should_have = (r_id in selected_ids)
                tags = r.setdefault("tags", [])
                has_tag = (tab_name in tags)
                if should_have and not has_tag:
                    tags.append(tab_name)
                    changed = True
                elif not should_have and has_tag:
                    tags.remove(tab_name)
                    changed = True
            if changed:
                self.store.save_rules()
                self.tabs[tab_name].refresh_table()
                self._refresh_tab_badges()
            dialog.destroy()

        ctk.CTkButton(btn_box, text="取消", width=90, fg_color="#475569", hover_color="#334155", command=dialog.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_box, text="確認儲存", width=100, fg_color="#10b981", hover_color="#059669", command=on_save).pack(side="right")

    def open_custom_tab_add_dialog(self, tab_name):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"在 [{tab_name}] 新增追蹤項目")
        dialog.geometry("450x360")
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 450) // 2
        y = self.winfo_y() + (self.winfo_height() - 360) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

        ctk.CTkLabel(dialog, text=f"【新增追蹤項目至 {tab_name}】", font=ctk.CTkFont(size=16, weight="bold"), text_color="#38bdf8").pack(pady=(20, 15))

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(padx=30, fill="x")

        ctk.CTkLabel(form, text="規範來源 (平台爬蟲):", font=("Helvetica", 13), anchor="w").pack(fill="x", pady=(5, 2))
        source_var = ctk.StringVar(value="IEC")
        source_menu = ctk.CTkOptionMenu(form, values=STANDARD_SOURCES, variable=source_var, width=320)
        source_menu.pack(pady=(0, 10))

        ctk.CTkLabel(form, text="關鍵字 / Standard_ID:", font=("Helvetica", 13), anchor="w").pack(fill="x", pady=(5, 2))
        keyword_entry = ctk.CTkEntry(form, placeholder_text="例如 60068-2-1 或 3A", width=320)
        keyword_entry.pack(pady=(0, 10))

        ctk.CTkLabel(form, text="查詢網址 (URL):", font=("Helvetica", 13), anchor="w").pack(fill="x", pady=(5, 2))
        url_entry = ctk.CTkEntry(form, placeholder_text="請貼上規範網頁完整網址", width=320)
        url_entry.pack(pady=(0, 15))

        def on_submit():
            src = source_var.get().strip()
            keyword = keyword_entry.get().strip()
            raw_url = url_entry.get().strip()
            if not keyword or not raw_url:
                messagebox.showerror("錯誤", "關鍵字與網址皆必填！")
                return

            clean_url = raw_url
            if src == "ASTM":
                from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
                parsed = urlparse(raw_url)
                qs = parse_qsl(parsed.query)
                qs_clean = [(k, v) for k, v in qs if not (k.startswith('_g') or k in ['fbclid', 'utm_source', 'utm_medium'])]
                clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(qs_clean), parsed.fragment))

            self.store.add_rule(keyword, clean_url, src, tags=[tab_name])
            self.refresh_tables()
            dialog.destroy()
            messagebox.showinfo("新增成功", f"已成功新增 [{src}] {keyword} 至 [{tab_name}]！")

        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(pady=10)
        ctk.CTkButton(btn_box, text="取消", width=90, fg_color="#475569", hover_color="#334155", command=dialog.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_box, text="新增", width=90, fg_color="#10b981", hover_color="#059669", command=on_submit).pack(side="left", padx=10)

    def check_custom_tab_updates(self, tab_name):
        rules = self.store.get_rules_by_tag(tab_name)
        if not rules:
            messagebox.showinfo("提示", f"自訂分頁 [{tab_name}] 目前沒有任何追蹤項目！")
            return

        sources = sorted(list({r.get("source") for r in rules if r.get("source")}))
        if not sources:
            messagebox.showinfo("提示", f"自訂分頁 [{tab_name}] 中的項目缺少來源分類！")
            return

        has_un = "UN" in sources
        if has_un:
            proceed = messagebox.askokcancel("提示", f"自訂分頁 [{tab_name}] 中包含 UN 資料，需要進行瀏覽器安全驗證。\n稍後將彈出驗證視窗，請勿移動或關閉，並配合完成驗證程序。\n\n確定要更新嗎？")
            if not proceed:
                return

        SCRAPER_MAP = {
            "IEC": self._run_iec_scraper,
            "ISTA": self._run_ista_scraper,
            "ANSI": self._run_ansi_scraper,
            "ASTM": self._run_astm_scraper,
            "DIN": self._run_din_scraper,
            "ETSI": self._run_etsi_scraper,
            "DNV": self._run_dnv_scraper,
            "EN": self._run_en_scraper,
            "ISO": self._run_iso_scraper,
            "JEDEC": self._run_jedec_scraper,
            "JIS": self._run_jis_scraper,
            "MIL": self._run_mil_scraper,
            "RTCA": self._run_rtca_scraper,
            "SAE": self._run_sae_scraper,
            "Telcordia": self._run_telcordia_scraper,
            "UN": self._run_un_scraper,
        }

        self._show_splash(title=f"正在更新自訂分頁 [{tab_name}]", subtitle="")
        self._update_splash_status("準備開始更新...", progress=0.0)

        def _run_custom():
            try:
                total_steps = len(sources)
                for i, src in enumerate(sources):
                    prog = (i + 1) / total_steps
                    self.after(0, lambda s=src, p=prog: self._update_splash_status(f"正在更新 {s}...", progress=p))
                    func = SCRAPER_MAP.get(src)
                    if func:
                        func(show_success_msg=False)
            finally:
                self.after(0, self.refresh_tables)
                self.after(0, self._refresh_tab_badges)
                self.after(0, lambda: self._update_splash_status("更新完成！", progress=1.0))
                self.after(500, self._dismiss_splash)
                self.after(600, lambda: messagebox.showinfo("更新完成", f"自訂分頁 [{tab_name}] 追蹤項目已更新完畢！"))

        threading.Thread(target=_run_custom, daemon=True).start()

    def select_tab(self, name):
        if self.active_tab == name:
            return
            
        old_active = self.active_tab
        self.active_tab = name

        # 隱藏先前的表格並更新樣式
        if old_active and old_active in self.tabs:
            self.tabs[old_active].pack_forget()
            self._update_single_tab_style(old_active)
            
        # 顯示新的表格並更新樣式
        if name in self.tabs:
            self.tabs[name].pack(fill="both", expand=True)
            self.tabs[name].refresh_table()
        self._update_single_tab_style(name)
        
        # 進入分頁後，自動清除該分類所有項目的「未讀提示」狀態 (不影響當日燈號)
        if name in self.settings.get("custom_tabs", []):
            rules = self.store.get_rules_by_tag(name)
        else:
            rules = self.store.get_rules_by_source(name)
        changed = False
        for r in rules:
            if r.get("tab_unread"):
                r["tab_unread"] = False
                self.store.update_rule(r)
                changed = True
        if changed:
            self._refresh_tab_badges()
        
        # 動態控制 API 除錯區域的顯示 (目前只有 ETSI 具有 API 除錯資訊)
        if hasattr(self, 'debug_frame'):
            if name == "ETSI":
                self.debug_frame.pack(padx=20, pady=(10, 20), fill="x")
            else:
                self.debug_frame.pack_forget()

    def open_add_dialog(self, source):
        if source in STANDARD_SOURCES:
            self._open_custom_add_dialog(source)
            return
            
        dialog = ctk.CTkInputDialog(text=f"請輸入要追蹤的 {source} Standard_ID (例如 3A):", title=f"新增 {source} 追蹤")
        query = dialog.get_input()
        if query:
            self.store.add_rule(query, query, source)
            self.refresh_tables()
            
    def _open_custom_add_dialog(self, source):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"新增 {source} 追蹤")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="關鍵字:").pack(pady=(20, 5))
        keyword_entry = ctk.CTkEntry(dialog, width=300)
        keyword_entry.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="網址:").pack(pady=(10, 5))
        url_entry = ctk.CTkEntry(dialog, width=300)
        url_entry.pack(pady=5)
        
        def on_submit():
            keyword = keyword_entry.get().strip()
            raw_url = url_entry.get().strip()
            if keyword and raw_url:
                clean_url = raw_url
                
                # 依照要求，只有 ASTM 才會清理追蹤參數，ANSI 則原封不動保留
                if source == "ASTM":
                    from urllib.parse import parse_qsl, urlencode
                    parsed = urlparse(raw_url)
                    qs = parse_qsl(parsed.query)
                    qs_clean = [(k, v) for k, v in qs if not (k.startswith('_g') or k in ['fbclid', 'utm_source', 'utm_medium'])]
                    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(qs_clean), parsed.fragment))
                
                self.store.add_rule(keyword, clean_url, source)
                self.refresh_tables()
                dialog.destroy()
            else:
                messagebox.showerror("錯誤", "關鍵字與網址皆必填！")
                
        ctk.CTkButton(dialog, text="新增", command=on_submit).pack(pady=20)
            
    def confirm_delete(self, rule_id, source):
        # messagebox is basic, but works
        confirm = messagebox.askyesno("刪除確認", "確定要刪除這筆追蹤規則嗎？")
        if confirm:
            self.store.remove_rule(rule_id)
            self.refresh_tables()

    def refresh_tables(self):
        for table in self.tabs.values():
            table.refresh_table()
        self._refresh_tab_badges()
        
    def _refresh_tab_badges(self):
        """掃描各分類與自訂分頁的更新狀態，改用綠色邊框高亮取代紅點"""
        has_global_update = any(r.get("tab_unread") for r in self.store.rules)
        self.set_app_badge(has_global_update)
        
        for name in list(self.tab_buttons.keys()):
            self._update_single_tab_style(name)

    def import_excel(self):
        file_path = filedialog.askopenfilename(
            title="選擇 Excel 檔案",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        success, msg = import_excel_rules(file_path, self.store)
        if success:
            messagebox.showinfo("匯入成功", msg)
            self.refresh_tables()
        else:
            messagebox.showerror("匯入失敗", msg)

    def export_excel(self):
        if not self.store.rules:
            messagebox.showwarning("提示", "目前沒有任何追蹤項目可供匯出！")
            return
            
        default_filename = f"規範追蹤清單_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        file_path = filedialog.asksaveasfilename(
            title="匯出 Excel 檔案",
            defaultextension=".xlsx",
            initialfile=default_filename,
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        success, msg = export_excel_rules(file_path, self.store.rules)
        if success:
            messagebox.showinfo("匯出成功", msg)
        else:
            messagebox.showerror("匯出失敗", msg)

    def show_loading(self, text="正在撈取資料，請稍候..."):
        self.loading_window = ctk.CTkToplevel(self)
        self.loading_window.title("載入中")
        self.loading_window.geometry("300x100")
        self.loading_window.transient(self)
        self.loading_window.grab_set() # 鎖定主視窗避免操作
        self.loading_window.protocol("WM_DELETE_WINDOW", lambda: None) # 禁用關閉按鈕
        
        self.loading_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 300) // 2
        y = self.winfo_y() + (self.winfo_height() - 100) // 2
        self.loading_window.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(self.loading_window, text=text, font=("Helvetica", 16)).pack(expand=True)
        self.update()

    def hide_loading(self):
        if hasattr(self, 'loading_window') and self.loading_window:
            self.loading_window.grab_release()
            self.loading_window.destroy()
            self.loading_window = None

    def _apply_rule_update(self, rule, new_version):
        latest_doc = rule.get("latestDocumentName", "")
        prev_doc = rule.get("previousDocumentName", "")
        
        # 若是剛匯入的資料，latest_doc 可能為空，此時將 Excel 帶入的 prev_doc 作為比較基準
        old_version = latest_doc if latest_doc else prev_doc
        
        # 為了避免空白格式不同導致誤判更新，比較時移除所有空白
        old_normalized = old_version.replace(" ", "") if old_version else ""
        new_normalized = new_version.replace(" ", "") if new_version else ""
        
        rule["previousDocumentName"] = old_version if old_version else "無資料"
        rule["latestDocumentName"] = new_version
        
        # 只有在「正規化後的字串」不同時，才視為有更新
        if old_version and old_version != "無資料" and new_normalized != old_normalized:
            rule["tab_unread"] = True
            rule["lastUpdatedDate"] = datetime.now().strftime("%Y-%m-%d")
            if hasattr(self, '_current_run_updated_rules') and isinstance(self._current_run_updated_rules, list):
                self._current_run_updated_rules.append({
                    "name": rule.get("name", ""),
                    "source": rule.get("source", ""),
                    "previousDocumentName": old_version,
                    "latestDocumentName": new_version,
                    "query": rule.get("query", "")
                })
        
        self.store.update_rule(rule)

    def check_category_updates(self, source):
        """按下各分頁的「更新」按鈕後，路由到對應的爬蟲函式"""
        SCRAPER_MAP = {
            "IEC": self._run_iec_scraper,
            "ISTA": self._run_ista_scraper,
            "ANSI": self._run_ansi_scraper,
            "ASTM": self._run_astm_scraper,
            "DIN": self._run_din_scraper,
            "ETSI": self._run_etsi_scraper,
            "DNV": self._run_dnv_scraper,
            "EN": self._run_en_scraper,
            "ISO": self._run_iso_scraper,
            "JEDEC": self._run_jedec_scraper,
            "JIS": self._run_jis_scraper,
            "MIL": self._run_mil_scraper,
            "RTCA": self._run_rtca_scraper,
            "SAE": self._run_sae_scraper,
            "Telcordia": self._run_telcordia_scraper,
            "UN": self._run_un_scraper,
        }
        run_func = SCRAPER_MAP.get(source)
        if run_func:
            if source == "UN":
                proceed = messagebox.askokcancel("提示", "UN資料庫需要進行瀏覽器安全驗證。\n稍後將彈出驗證視窗，請勿移動或關閉，並配合完成驗證程序。\n\n確定要繼續嗎？")
                if not proceed:
                    return
                self.show_loading(f"進行瀏覽器驗證中...")
            else:
                self.show_loading(f"正在更新 {source}...")
            threading.Thread(target=run_func, daemon=True).start()

    def _run_un_scraper(self, show_success_msg=True):
        self._run_generic_scraper("UN", check_un_updates, show_success_msg)

    def check_all_updates(self, is_auto=False):
        if getattr(self, '_is_batch_updating', False):
            if not is_auto:
                messagebox.showinfo("提示", "目前已有更新作業正在執行中，請稍候！")
            return
        self._is_batch_updating = True
        self._current_run_updated_rules = []
        has_un = any(rule.get("source") == "UN" for rule in self.store.rules)
        if has_un and not is_auto:
            proceed = messagebox.askokcancel("提示", "更新佇列中包含 UN 資料，需要進行瀏覽器安全驗證。\n稍後將彈出驗證視窗，請勿移動或關閉，並配合完成驗證程序。\n\n確定要更新嗎？")
            if not proceed:
                self._is_batch_updating = False
                return
            
        self._show_splash(title="更新中，請勿關閉程式", subtitle="")
        self._update_splash_status("準備開始全面更新...", progress=0.0)

        def _run_all():
            try:
                tasks = [
                    ("IEC", self._run_iec_scraper),
                    ("ISTA", self._run_ista_scraper),
                    ("ANSI", self._run_ansi_scraper),
                    ("ASTM", self._run_astm_scraper),
                    ("DIN", self._run_din_scraper),
                    ("ETSI", self._run_etsi_scraper),
                    ("DNV", self._run_dnv_scraper),
                    ("EN", self._run_en_scraper),
                    ("ISO", self._run_iso_scraper),
                    ("JEDEC", self._run_jedec_scraper),
                    ("JIS", self._run_jis_scraper),
                    ("MIL", self._run_mil_scraper),
                    ("RTCA", self._run_rtca_scraper),
                    ("SAE", self._run_sae_scraper),
                    ("Telcordia", self._run_telcordia_scraper)
                ]
                
                total_steps = len(tasks)
                if has_un:
                    total_steps += 1
                    self.after(0, lambda: self._update_splash_status("正在更新 UN (需要瀏覽器驗證)...", progress=1/total_steps))
                    self._run_un_scraper(show_success_msg=False)
                
                for i, (name, func) in enumerate(tasks):
                    current_step = (2 if has_un else 1) + i
                    prog = current_step / total_steps
                    self.after(0, lambda n=name, p=prog: self._update_splash_status(f"正在更新 {n}...", progress=p))
                    func(show_success_msg=False)
                    
            finally:
                self._is_batch_updating = False
                self.after(0, self._refresh_tab_badges)
                self.after(0, lambda: self._update_splash_status("更新完成！", progress=1.0))
                self.after(500, self._dismiss_splash)
                if not is_auto:
                    self.after(600, lambda: messagebox.showinfo("更新完成", "所有追蹤項目更新完畢！"))
                else:
                    self._handle_auto_update_teams_notification(list(self._current_run_updated_rules))
                
        threading.Thread(target=_run_all, daemon=True).start()

    def _handle_auto_update_teams_notification(self, updated_rules):
        """每日自動排程更新完成後發送 Microsoft Teams 通知 (有更新列出清單，無更新亦回報；手動更新不觸發)"""
        try:
            if not self.settings.get("teams_enabled", False):
                return
            webhook_url = (self.settings.get("teams_webhook_url", "") or "").strip()
            if not webhook_url:
                return

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            total_rules_count = len(self.store.rules) if hasattr(self, 'store') and self.store and hasattr(self.store, 'rules') else 0

            if updated_rules:
                title = "📢 【標準法規追蹤系統】每日排程更新通知"
                summary = f"系統於 {now_str} 完成每日自動排程更新，共檢查 {total_rules_count} 項標準，發現 **{len(updated_rules)}** 項法規有最新版本異動："
            else:
                title = "✅ 【標準法規追蹤系統】每日排程檢查報告"
                summary = f"系統於 {now_str} 完成每日自動排程檢查，共檢查 {total_rules_count} 項標準。"

            send_teams_notification(
                webhook_url=webhook_url,
                title=title,
                summary=summary,
                updated_items=updated_rules,
                total_count=total_rules_count,
                is_test=False
            )
        except Exception as e:
            print(f"[Teams Notification Error] {e}")


    def _run_generic_scraper(self, source_name, scraper_func, show_success_msg=True):
        try:
            rules = self.store.rules
            items = [{"keyword": r["name"], "url": r["query"]} for r in rules if r["source"] == source_name]
            
            if not items:
                if show_success_msg:
                    self.after(0, self.hide_loading)
                    messagebox.showinfo("更新完成", f"目前沒有追蹤任何 {source_name} 項目！")
                return
            
            # 移除在這邊的 URL 去重邏輯，因為像 ISTA 這種來源，同一個 URL 會有多個不同的關鍵字 (例如 1A, 3A)，
            # 它們的版本日期不同。把去重的工作交給各個爬蟲內部自行處理。
            updates = scraper_func(items)
            
            if updates:
                # 建立 Keyword (小寫) 對應 Date 的字典
                kw_to_date = {u.get("keyword", "").strip().lower(): u.get("date", "") for u in updates if u.get("keyword")}

                for r in rules:
                    if r["source"] == source_name:
                        r_kw = r["name"].strip().lower()
                        if r_kw in kw_to_date:
                            new_version = normalize_date(kw_to_date[r_kw])
                            self._apply_rule_update(r, new_version)
                            
                self.after(0, self.refresh_tables)
                
                # 爬蟲結束後，讓主視窗回到最上層，提醒使用者
                self.after(0, self.lift)
                self.after(0, lambda: self.attributes('-topmost', True))
                self.after(500, lambda: self.attributes('-topmost', False))

                
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("更新失敗", f"{source_name} 爬蟲發生錯誤: {str(e)}"))
        finally:
            if show_success_msg:
                self.after(0, self.hide_loading)

    def _run_ansi_scraper(self, show_success_msg=True):
        self._run_generic_scraper("ANSI", check_ansi_updates, show_success_msg)
    def _run_astm_scraper(self, show_success_msg=True):
        self._run_generic_scraper("ASTM", check_astm_updates, show_success_msg)
    def _run_din_scraper(self, show_success_msg=True):
        self._run_generic_scraper("DIN", check_din_updates, show_success_msg)
    def _run_etsi_scraper(self, show_success_msg=True):
        self._run_generic_scraper("ETSI", check_etsi_updates, show_success_msg)
    def _run_ista_scraper(self, show_success_msg=True):
        self._run_generic_scraper("ISTA", check_ista_updates, show_success_msg)
    def _run_dnv_scraper(self, show_success_msg=True):
        self._run_generic_scraper("DNV", check_dnv_updates, show_success_msg)
    def _run_en_scraper(self, show_success_msg=True):
        self._run_generic_scraper("EN", check_en_updates, show_success_msg)
    def _run_iso_scraper(self, show_success_msg=True):
        self._run_generic_scraper("ISO", check_iso_updates, show_success_msg)
    def _run_jedec_scraper(self, show_success_msg=True):
        self._run_generic_scraper("JEDEC", check_jedec_updates, show_success_msg)
    def _run_jis_scraper(self, show_success_msg=True):
        self._run_generic_scraper("JIS", check_jis_updates, show_success_msg)
    def _run_mil_scraper(self, show_success_msg=True):
        self._run_generic_scraper("MIL", check_mil_updates, show_success_msg)
    def _run_rtca_scraper(self, show_success_msg=True):
        self._run_generic_scraper("RTCA", check_rtca_updates, show_success_msg)
    def _run_sae_scraper(self, show_success_msg=True):
        self._run_generic_scraper("SAE", check_sae_updates, show_success_msg)
    def _run_telcordia_scraper(self, show_success_msg=True):
        self._run_generic_scraper("Telcordia", check_telcordia_updates, show_success_msg)

    def run_single_update(self, rule):
        """針對單一 rule 啟動對應的爬蟲，只更新那一筆"""
        source = rule.get("source", "")
        if source == "UN":
            proceed = messagebox.askokcancel("提示", "UN資料庫需要進行瀏覽器安全驗證。\n稍後將彈出驗證視窗，請勿移動或關閉，並配合完成驗證程序。\n\n確定要繼續嗎？")
            if not proceed:
                return
            self.show_loading(f"進行瀏覽器驗證中...")
        else:
            self.show_loading(f"正在更新 {rule.get('name', '')}...")
        
        # 爬蟲 source -> 函式 的對照表
        SCRAPER_MAP = {
            "IEC": check_iec_updates,
            "ISTA": check_ista_updates,
            "ANSI": check_ansi_updates,
            "ASTM": check_astm_updates,
            "DIN": check_din_updates,
            "ETSI": check_etsi_updates,
            "DNV": check_dnv_updates,
            "EN": check_en_updates,
            "ISO": check_iso_updates,
            "JEDEC": check_jedec_updates,
            "JIS": check_jis_updates,
            "MIL": check_mil_updates,
            "RTCA": check_rtca_updates,
            "SAE": check_sae_updates,
            "Telcordia": check_telcordia_updates,
            "UN": check_un_updates
        }
        
        scraper_fn = SCRAPER_MAP.get(source)
        
        def _run():
            try:
                if not scraper_fn:
                    self.after(0, lambda: messagebox.showinfo("提示", f"{source} 尚未實作爬蟲！"))
                    return
                    
                item = {"keyword": rule["name"], "url": rule.get("query", "")}
                updates = scraper_fn([item])
                
                if updates:
                    u = updates[0]
                    new_version = normalize_date(u.get("date", ""))
                    self._apply_rule_update(rule, new_version)
                    self.after(0, self.refresh_tables)
                    
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("更新失敗", f"單筆更新發生錯誤: {str(e)}"))
            finally:
                self.after(0, self.hide_loading)
                
        threading.Thread(target=_run, daemon=True).start()

    def _run_iec_scraper(self, show_success_msg=True):
        self._run_generic_scraper("IEC", check_iec_updates, show_success_msg)


def check_lan_access():
    """開啟前確認在公司區網內（能存取 config.json 設定的 NAS 資料夾）。未設定則略過。"""
    import tkinter as tk
    from tkinter import messagebox
    nas = load_config().get("nas_folder", "")
    if check_lan(nas) == 'failed':
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "無法開啟",
            "偵測到目前未連接公司內部網路，無法開啟此應用程式。\n\n"
            "請連接公司網路後再試。"
        )
        sys.exit()


if __name__ == "__main__":
    check_lan_access()
    app = App()
    app.mainloop()
