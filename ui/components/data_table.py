import customtkinter as ctk
import webbrowser
from datetime import datetime
from ui.components.tooltip import ToolTip

class DataTable(ctk.CTkFrame):
    def __init__(self, master, rules_store, source, is_custom=False, on_delete=None, on_add=None, on_update=None, on_row_update=None, on_select_existing=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.rules_store = rules_store
        self.source = source
        self.is_custom = is_custom
        self.on_delete = on_delete
        self.on_add = on_add
        self.on_update = on_update
        self.on_row_update = on_row_update
        self.on_select_existing = on_select_existing
        
        # Tool Bar (Category specific actions)
        self.toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar_frame.pack(side="top", fill="x", pady=(15, 10))

        self.btn_update = ctk.CTkButton(self.toolbar_frame, text="更新", width=100, command=self._update_clicked)
        self.btn_update.pack(side="right", padx=5)
        
        self.btn_add = ctk.CTkButton(self.toolbar_frame, text="新增追蹤", width=100, fg_color="gray30", command=self._add_clicked)
        self.btn_add.pack(side="right", padx=5)

        if self.is_custom:
            self.btn_select_existing = ctk.CTkButton(
                self.toolbar_frame, 
                text="從現有項目挑選", 
                width=120, 
                fg_color="#0284c7", 
                hover_color="#0369a1", 
                command=self._select_existing_clicked
            )
            self.btn_select_existing.pack(side="right", padx=5)

        # Header Row
        self.header_frame = ctk.CTkFrame(self, height=40, fg_color="#343638", corner_radius=0)
        self.header_frame.pack(side="top", fill="x")
        
        ctk.CTkLabel(self.header_frame, text="狀態", width=65 if self.is_custom else 80, font=("Helvetica", 13, "bold")).pack(side="left", padx=5)
        if self.is_custom:
            ctk.CTkLabel(self.header_frame, text="規範來源", width=90, font=("Helvetica", 13, "bold"), anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(self.header_frame, text="Standard_ID", width=180 if self.is_custom else 200, font=("Helvetica", 13, "bold"), anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(self.header_frame, text="Previous_Version", width=160, font=("Helvetica", 13, "bold"), anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(self.header_frame, text="Current_Version", font=("Helvetica", 13, "bold"), anchor="w").pack(side="left", fill="x", expand=True, padx=5)
        
        # 由右至左排列：操作 -> 查看
        ctk.CTkLabel(self.header_frame, text="操作", width=140, font=("Helvetica", 13, "bold")).pack(side="right", padx=5)
        
        # Scrollable Data Area
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(side="top", fill="both", expand=True)
        
        self.rows = []
        self.refresh_table()

    def refresh_table(self):
        # Clear existing items
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.rows.clear()
            
        if self.is_custom:
            rules = self.rules_store.get_rules_by_tag(self.source)
        else:
            rules = self.rules_store.get_rules_by_source(self.source)
        
        for i, rule in enumerate(rules):
            bg_color = "#2b2b2b" if i % 2 == 0 else "#242424"
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color=bg_color, corner_radius=0, height=50)
            row_frame.pack(side="top", fill="x", pady=1)
            row_frame.pack_propagate(False)
            
            today_str = datetime.now().strftime("%Y-%m-%d")
            last_updated = rule.get("lastUpdatedDate")
            
            is_updated = (last_updated == today_str)
            status_text = "●"
            status_color = "#10b981" if is_updated else "#52525b"
            
            prev_doc = rule.get("previousDocumentName", "")
            latest_doc = rule.get("latestDocumentName", "")
            
            if not prev_doc or prev_doc == "無資料":
                prev_doc = latest_doc if latest_doc else "尚未檢查"
            if not latest_doc or latest_doc == "無資料":
                curr_doc = prev_doc if prev_doc else "尚未檢查"
            else:
                curr_doc = latest_doc
                
            ctk.CTkLabel(row_frame, text=status_text, text_color=status_color, width=65 if self.is_custom else 80, font=("Helvetica", 20)).pack(side="left", padx=5)
            
            # 若為自訂分頁，顯示所屬來源
            if self.is_custom:
                src_container = ctk.CTkFrame(row_frame, width=90, fg_color="transparent")
                src_container.pack(side="left", padx=5)
                src_container.pack_propagate(False)
                ctk.CTkLabel(
                    src_container, 
                    text=rule.get("source", "IEC"), 
                    font=("Helvetica", 12, "bold"), 
                    text_color="#38bdf8", 
                    anchor="w"
                ).pack(fill="both", expand=True)

            # 用固定寬度的容器 Frame 強制限制 Standard_ID 欄寬，避免長文字溢出
            name_container_width = 180 if self.is_custom else 200
            name_container = ctk.CTkFrame(row_frame, width=name_container_width, fg_color="transparent")
            name_container.pack(side="left", padx=5)
            name_container.pack_propagate(False)  # 鎖定容器寬度，禁止被內容撐大
            # 文字太長時截斷加 ...
            name_text = rule["name"]
            max_char = 22 if self.is_custom else 26
            if len(name_text) > max_char:
                name_text = name_text[:max_char - 2] + "..."
            name_label = ctk.CTkLabel(name_container, text=name_text, anchor="w", justify="left")
            name_label.pack(fill="both", expand=True)
            # Tooltip 顯示完整名稱（如果有被截斷）
            if rule["name"] != name_text:
                ToolTip(name_label, text=rule["name"])
            
            # Previous_Version 欄位
            prev_container = ctk.CTkFrame(row_frame, width=160, fg_color="transparent")
            prev_container.pack(side="left", padx=5)
            prev_container.pack_propagate(False)
            ctk.CTkLabel(prev_container, text=prev_doc, text_color="#9ca3af", anchor="w", justify="left").pack(fill="both", expand=True)

            # Current_Version 欄位 (有更新時高亮為綠色)
            curr_color = "#10b981" if is_updated else "white"
            ctk.CTkLabel(row_frame, text=curr_doc, text_color=curr_color, anchor="w", justify="left").pack(side="left", fill="x", expand=True, padx=5)
            
            # 由右至左：刪除/移出 -> 查看
            if self.is_custom:
                del_btn = ctk.CTkButton(row_frame, text="移出", width=55, height=24, fg_color="#d97706", hover_color="#b45309")
                ToolTip(del_btn, text="從自訂分頁移出 (保留原分類中的資料)")
            else:
                del_btn = ctk.CTkButton(row_frame, text="刪除", width=55, height=24, fg_color="#b91c1c", hover_color="#991b1b")
            del_btn.configure(command=lambda r_id=rule["id"]: self._delete_clicked(r_id))
            del_btn.pack(side="right", padx=(0, 10))
            
            link_btn = ctk.CTkButton(
                row_frame, 
                text="查看", 
                width=55, 
                height=24, 
                fg_color="transparent", 
                border_width=1,
                border_color="#3b82f6",
                text_color="#3b82f6", 
                hover_color="#1e3a8a", 
                command=lambda u=rule.get("query", ""): webbrowser.open(u) if u else None
            )
            link_btn.pack(side="right", padx=4)
            
            # Hover ToolTip 顯示完整網址
            url_text = rule.get("query", "無網址")
            ToolTip(link_btn, text=url_text)
            
            self.rows.append(row_frame)

    def _delete_clicked(self, rule_id):
        if self.on_delete:
            self.on_delete(rule_id, self.source)

    def _add_clicked(self):
        if self.on_add:
            self.on_add(self.source)
            
    def _update_clicked(self):
        if self.on_update:
            self.on_update(self.source)
            
    def _row_update_clicked(self, rule):
        if self.on_row_update:
            self.on_row_update(rule)

    def _select_existing_clicked(self):
        if self.on_select_existing:
            self.on_select_existing(self.source)
