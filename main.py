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
from core.excel_importer import import_excel_rules
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
from urllib.parse import urlparse, urlunparse
import threading
import time

# Basic CTk Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Standardized Inspection System")
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
        self.bind("<FocusIn>", self._clear_app_badge)

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
        import platform
        if active:
            self._badge_active = True
        if platform.system() == "Windows":
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    import os
                    from PIL import Image
                    icon_name = 'tray_icon_alert.png' if active else 'tray_icon.png'
                    icon_path = os.path.join(os.path.dirname(__file__), 'assets', icon_name)
                    if os.path.exists(icon_path):
                        self.tray_icon.icon = Image.open(icon_path)
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

    def _clear_app_badge(self, event=None):
        if getattr(self, '_badge_active', False):
            self._badge_active = False
            self.set_app_badge(False)

    def setup_tray_icon(self):
        import platform
        if platform.system() == "Windows":
            menu = (
                item('開啟', self.on_tray_show, default=True),
                item('結束應用程式', self.on_tray_quit)
            )
            self.tray_icon = pystray.Icon("SIS", self._get_tray_image(), "標準檢驗追蹤系統", menu)
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

    def _show_splash(self, title="Standardized Inspection System", subtitle=""):
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
        
        # 啟動時自動進行一次全域的日期格式修復 (套用最新版 date_utils 修正之前存留的錯字或缺空白)
        changed = False
        from core.date_utils import normalize_date
        for r in self.store.rules:
            old_p = r.get("previousDocumentName", "")
            old_l = r.get("latestDocumentName", "")
            new_p = normalize_date(old_p) if old_p else old_p
            new_l = normalize_date(old_l) if old_l else old_l
            
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

        # Header Frame
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", padx=20, pady=(20, 10))
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="監控總覽", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left")

        # Action Buttons
        self.btn_update_all = ctk.CTkButton(self.header_frame, text="更新全部追蹤", command=self.check_all_updates)
        self.btn_update_all.pack(side="right", padx=5)
        
        self.btn_import_excel = ctk.CTkButton(self.header_frame, text="匯入 Excel", fg_color="#10b981", hover_color="#059669", command=self.import_excel)
        self.btn_import_excel.pack(side="right", padx=5)
        
        self.btn_clear_all = ctk.CTkButton(self.header_frame, text="清除所有追蹤", fg_color="#b91c1c", hover_color="#991b1b", width=90, command=self.clear_all_data)
        self.btn_clear_all.pack(side="right", padx=5)
        
        self.btn_auto_update = ctk.CTkButton(self.header_frame, text="時間設定", fg_color="#3b82f6", hover_color="#2563eb", width=90, command=self._open_auto_update_settings)
        self.btn_auto_update.pack(side="right", padx=5)

        self.btn_auth_settings = ctk.CTkButton(self.header_frame, text="權限設定", fg_color="#6366f1", hover_color="#4f46e5", width=90, command=self._open_auth_settings)
        self.btn_auth_settings.pack(side="right", padx=5)

        # Tab Menu
        self.tab_menu_frame = ctk.CTkScrollableFrame(self.main_container, orientation="horizontal", height=45, fg_color="transparent")
        self.tab_menu_frame.pack(side="top", fill="x", padx=20, pady=(0, 5))
        
        self.tabs = {}
        self.tab_buttons = {}
        self.active_tab = None
        self.tab_col = 0
        self.tab_row = 0
        
        # Tab Content Area
        self.tab_content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_content_area.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 設定要初始化的分頁佇列
        # 分頁順序：將 DNV 移到 DIN, ETSI 前面
        self._tabs_to_init = ["IEC", "ISTA", "ANSI", "ASTM", "DNV", "DIN", "ETSI", "EN", "ISO", "JEDEC", "JIS", "MIL", "RTCA", "SAE", "Telcordia", "UN"]
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
        self.debug_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.debug_btn = ctk.CTkButton(self.debug_frame, text="▶ 展開 API 除錯資訊", command=self.toggle_debug)
        self.debug_btn.pack(anchor="w")
        self.debug_text = ctk.CTkTextbox(self.debug_frame, width=800, height=250)
        self.debug_text.insert("0.0", "系統準備就緒...\n")
        
        self._update_splash_status("即將完成...", progress=0.95)
        self.select_tab("IEC")
        self.refresh_tables()
        
        # 強制 Tkinter 在背景把所有的排版、表格內容都計算與繪製完畢
        self.update_idletasks()
        
        # 進度跑到 100% 後，短暫停留 400ms 讓使用者看見「完成」狀態再移除蓋板
        self._update_splash_status("完成！", progress=1.0)
        self.after(400, self._dismiss_splash)

    def _dismiss_splash(self):
        """移除覆蓋層，顯示已建好的主畫面"""
        if hasattr(self, 'splash_overlay') and self.splash_overlay.winfo_exists():
            self.splash_overlay.destroy()
            self._start_auto_update_loop()

    def _start_auto_update_loop(self):
        self._check_auto_update()

    def _check_auto_update(self):
        target_time = self.settings.get("auto_update_time", "")
        if target_time:
            from datetime import datetime
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


    def _open_auth_settings(self):
        auth_win = ctk.CTkToplevel(self)
        auth_win.title("系統權限設定")
        auth_win.geometry("400x250")
        auth_win.resizable(False, False)
        auth_win.transient(self)
        auth_win.grab_set()
        auth_win.focus_force()

        ctk.CTkLabel(
            auth_win,
            text="設定允許開啟系統的網域",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            auth_win,
            text="若留白，則不限制任何人開啟；\n若輸入網域 (例如 IST)，則僅限該網域電腦可開啟。",
            text_color="#9ca3af"
        ).pack(pady=(0, 20))

        domain_var = ctk.StringVar(value=self.settings.get("allowed_domain", ""))
        
        entry = ctk.CTkEntry(
            auth_win, 
            textvariable=domain_var,
            placeholder_text="例如: IST",
            width=200
        )
        entry.pack(pady=(0, 20))

        def save_auth():
            new_domain = domain_var.get().strip().upper()
            self.settings.set("allowed_domain", new_domain)
            if new_domain:
                messagebox.showinfo("儲存成功", f"已設定允許網域為：{new_domain}\n下次啟動時將生效。")
            else:
                messagebox.showinfo("儲存成功", "已清除網域限制，所有電腦皆可開啟系統。")
            auth_win.destroy()

        ctk.CTkButton(
            auth_win,
            text="儲存設定",
            command=save_auth,
            fg_color="#10b981",
            hover_color="#059669"
        ).pack()

    def _open_auto_update_settings(self):
        current_time = self.settings.get("auto_update_time", "")
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("自動更新設定")
        dialog.geometry("400x260")
        dialog.transient(self)
        dialog.grab_set()
        
        # 讓視窗置中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 260) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(
            dialog, 
            text="請輸入每日自動更新時間",
            justify="center"
        ).pack(pady=(30, 10))
        
        input_frame = ctk.CTkFrame(dialog, fg_color="transparent")
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
            
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_confirm():
            h_val = entry_h.get().strip()
            m_val = entry_m.get().strip()
            
            if not h_val or not m_val:
                import tkinter.messagebox as messagebox
                messagebox.showerror("錯誤", "小時與分鐘皆不可為空！\n(若要取消排程，請點擊「清除設定」)", parent=dialog)
                return
                
            try:
                h_int = int(h_val)
                m_int = int(m_val)
                if not (0 <= h_int <= 23 and 0 <= m_int <= 59):
                    raise ValueError
            except ValueError:
                import tkinter.messagebox as messagebox
                messagebox.showerror("錯誤", "請輸入有效的時間格式\n小時: 0-23, 分鐘: 0-59", parent=dialog)
                return
                
            result = f"{h_int:02d}:{m_int:02d}"
            self.settings.set("auto_update_time", result)
            self.settings.set("last_auto_update_date", "")
            dialog.destroy()
            import tkinter.messagebox as messagebox
            messagebox.showinfo("設定成功", f"已設定每日 {result} 自動更新！")
            
        def on_clear():
            self.settings.set("auto_update_time", "")
            self.settings.set("last_auto_update_date", "")
            dialog.destroy()
            import tkinter.messagebox as messagebox
            messagebox.showinfo("設定成功", "已清除每日自動更新。")
            
        def on_cancel():
            dialog.destroy()
            
        btn_cancel = ctk.CTkButton(btn_frame, text="取消", width=80, fg_color="#52525b", hover_color="#3f3f46", command=on_cancel)
        btn_cancel.pack(side="left", padx=10)
        
        btn_clear = ctk.CTkButton(btn_frame, text="清除設定", width=80, fg_color="#b91c1c", hover_color="#991b1b", command=on_clear)
        btn_clear.pack(side="left", padx=10)
        
        btn_ok = ctk.CTkButton(btn_frame, text="確定", width=80, command=on_confirm)
        btn_ok.pack(side="left", padx=10)
        
        dialog.bind("<Return>", lambda event: on_confirm())
        dialog.bind("<Escape>", lambda event: on_cancel())

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
            on_delete=self.confirm_delete,
            on_add=self.open_add_dialog,
            on_update=self.check_category_updates,
            on_row_update=self.run_single_update
        )
        self.tabs[name] = table

    def select_tab(self, name):
        if self.active_tab == name:
            return
            
        # 隱藏目前的表格，並將按鈕顏色調暗
        if self.active_tab:
            self.tabs[self.active_tab].pack_forget()
            self.tab_buttons[self.active_tab].configure(fg_color="transparent", text_color="gray")
            
        # 顯示新的表格，並將按鈕顏色調亮 (模擬選中狀態)
        self.tabs[name].pack(fill="both", expand=True)
        self.tab_buttons[name].configure(fg_color="#1f538d", text_color="white", text=name)
        
        self.active_tab = name
        
        # 進入分頁後，自動清除該分類所有項目的「未讀提示」狀態 (不影響當日燈號)
        rules = self.store.get_rules_by_source(name)
        changed = False
        for r in rules:
            if r.get("tab_unread"):
                r["tab_unread"] = False
                self.store.update_rule(r)
                changed = True
        if changed:
            self.after(0, self.refresh_tables)
        
        # 動態控制 API 除錯區域的顯示 (目前只有 ETSI 具有 API 除錯資訊)
        if hasattr(self, 'debug_frame'):
            if name == "ETSI":
                self.debug_frame.pack(padx=20, pady=(10, 20), fill="x")
            else:
                self.debug_frame.pack_forget()

    def open_add_dialog(self, source):
        if source in ["IEC", "ASTM", "ANSI", "ISTA", "DNV", "DIN", "ETSI", "EN", "ISO", "JEDEC", "JIS", "MIL", "RTCA", "SAE", "Telcordia", "UN"]:
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
        """掃描各分類的更新狀態，改用綠色邊框高亮取代紅點"""
        for source, btn in self.tab_buttons.items():
            rules = self.store.get_rules_by_source(source)
            has_update = any(r.get("tab_unread") for r in rules)
            
            is_active = (self.active_tab == source)
            
            if has_update:
                # 有更新：加上綠色邊框
                btn.configure(
                    text=source,
                    border_width=2,
                    border_color="#10b981",
                    fg_color="#1f538d" if is_active else "transparent",
                    text_color="white" if is_active else "#10b981"
                )
            else:
                # 無更新：清除邊框，恢復正常
                btn.configure(
                    text=source,
                    border_width=0,
                    fg_color="#1f538d" if is_active else "transparent",
                    text_color="white" if is_active else "gray"
                )

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
        from datetime import datetime
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
            self.after(0, lambda: self.set_app_badge(True))
        
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
        has_un = any(rule.get("source") == "UN" for rule in self.store.rules)
        if has_un and not is_auto:
            proceed = messagebox.askokcancel("提示", "更新佇列中包含 UN 資料，需要進行瀏覽器安全驗證。\n稍後將彈出驗證視窗，請勿移動或關閉，並配合完成驗證程序。\n\n確定要更新嗎？")
            if not proceed:
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
                self.after(0, lambda: self._update_splash_status("更新完成！", progress=1.0))
                self.after(500, self._dismiss_splash)
                self.after(600, lambda: messagebox.showinfo("更新完成", "所有追蹤項目更新完畢！"))
                
        threading.Thread(target=_run_all, daemon=True).start()


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


def check_domain_access():
    import platform
    import os
    import sys
    import json
    from tkinter import messagebox
    import tkinter as tk
    
    # 從 settings.json 讀取網域設定
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    allowed_domain = ""
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                allowed_domain = data.get("allowed_domain", "").strip().upper()
        except:
            pass
            
    # 如果還沒有設定網域，預設為全部放行
    if not allowed_domain:
        return True
    
    # 獲取 Windows 當前登入的網域
    current_domain = os.environ.get('USERDOMAIN', '').upper()
    
    # 若不在允許名單內，跳出錯誤並強制關閉
    if current_domain != allowed_domain:
        root = tk.Tk()
        root.withdraw() # 隱藏主視窗
        messagebox.showerror(
            "權限錯誤",
            f"您無權限開啟此應用程式。\n\n"
            f"原因：不在授權的公司網域內 (限定: {allowed_domain})。\n"
            f"偵測到的網域：{current_domain if current_domain else '未知'}"
        )
        sys.exit()

if __name__ == "__main__":
    check_domain_access()
    app = App()
    app.mainloop()
