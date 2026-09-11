import customtkinter as ctk
from tkinter import ttk
import tkinter as tk
import webbrowser
from ui.components.tooltip import ToolTip

class DataTable(ctk.CTkFrame):
    def __init__(self, master, rules_store, source, on_delete=None, on_add=None, on_update=None, on_row_update=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.rules_store = rules_store
        self.source = source
        self.on_delete = on_delete
        self.on_add = on_add
        self.on_update = on_update
        self.on_row_update = on_row_update
        
        # Tool Bar (Category specific actions)
        self.toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar_frame.pack(side="top", fill="x", pady=(15, 10))
        
        self.btn_update = ctk.CTkButton(self.toolbar_frame, text="更新", width=100, command=self._update_clicked)
        self.btn_update.pack(side="right", padx=5)
        
        self.btn_add = ctk.CTkButton(self.toolbar_frame, text="新增追蹤", width=100, fg_color="gray30", command=self._add_clicked)
        self.btn_add.pack(side="right", padx=5)

        # Header Row
        self.header_frame = ctk.CTkFrame(self, height=40, fg_color="#343638", corner_radius=0)
        self.header_frame.pack(side="top", fill="x")
        
        ctk.CTkLabel(self.header_frame, text="狀態", width=80, font=("Helvetica", 13, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(self.header_frame, text="Standard_ID", width=220, font=("Helvetica", 13, "bold"), anchor="w").pack(side="left", padx=5)
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
            
        rules = self.rules_store.get_rules_by_source(self.source)
        
        for i, rule in enumerate(rules):
            bg_color = "#2b2b2b" if i % 2 == 0 else "#242424"
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color=bg_color, corner_radius=0, height=50)
            row_frame.pack(side="top", fill="x", pady=1)
            row_frame.pack_propagate(False)
            
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")
            last_updated = rule.get("lastUpdatedDate")
            
            is_updated = (last_updated == today_str)
            status_text = "●"
            status_color = "#10b981" if is_updated else "#52525b"
            
            doc_name = rule.get("latestDocumentName")
            if not doc_name or doc_name == "無資料":
                doc_name = rule.get("previousDocumentName", "尚未檢查")
                
            ctk.CTkLabel(row_frame, text=status_text, text_color=status_color, width=80, font=("Helvetica", 20)).pack(side="left", padx=5)
            
            # 用固定寬度的容器 Frame 強制限制 Standard_ID 欄寬，避免長文字溢出
            name_container = ctk.CTkFrame(row_frame, width=220, fg_color="transparent")
            name_container.pack(side="left", padx=5)
            name_container.pack_propagate(False)  # 鎖定容器寬度，禁止被內容撐大
            # 文字太長時截斷加 ...
            name_text = rule["name"]
            if len(name_text) > 28:
                name_text = name_text[:26] + "..."
            name_label = ctk.CTkLabel(name_container, text=name_text, anchor="w", justify="left")
            name_label.pack(fill="both", expand=True)
            # Tooltip 顯示完整名稱（如果有被截斷）
            if rule["name"] != name_text:
                from ui.components.tooltip import ToolTip as TT
                TT(name_label, text=rule["name"])
            
            ctk.CTkLabel(row_frame, text=doc_name, anchor="w", justify="left").pack(side="left", fill="x", expand=True, padx=5)
            
            # 由右至左：刪除 -> 查看
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
