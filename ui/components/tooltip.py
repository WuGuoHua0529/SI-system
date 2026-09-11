import tkinter as tk

class ToolTip:
    def __init__(self, widget, text, wrap_length=400):
        self.widget = widget
        self.text = text
        self.wrap_length = wrap_length
        self.tip_window = None
        
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        
    def enter(self, event=None):
        self.schedule_id = self.widget.after(300, self.show_tip)
        
    def leave(self, event=None):
        if hasattr(self, 'schedule_id'):
            self.widget.after_cancel(self.schedule_id)
        self.hide_tip()
        
    def show_tip(self):
        if self.tip_window or not self.text:
            return
            
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True) # 無邊框
        tw.wm_geometry(f"+{x}+{y}")
        
        # 深色主題提示框
        label = tk.Label(
            tw, 
            text=self.text, 
            justify=tk.LEFT,
            background="#1e1e1e", 
            foreground="#e0e0e0", 
            relief=tk.SOLID, 
            borderwidth=1,
            wraplength=self.wrap_length,
            font=("Helvetica", 12)
        )
        label.pack(ipadx=8, ipady=4)
        
    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()
