"""可复用 GUI 组件。"""

import tkinter as tk
from tkinter import ttk


def format_size(size_bytes):
    """将字节数格式化为人类可读的大小字符串。"""
    if size_bytes < 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            if unit == "B":
                return f"{size_bytes} B"
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


class ProgressDialog(tk.Toplevel):
    """模态进度条对话框，支持取消操作。"""

    def __init__(self, parent, title="请稍候", message="正在扫描...", cancellable=False):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._cancelled = False
        self._cancellable = cancellable

        # 居中（高度根据是否有取消按钮调整）
        win_h = 160 if cancellable else 130
        self.geometry(f"440x{win_h}")
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 440) // 2
        y = parent.winfo_y() + (parent.winfo_height() - win_h) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        self.label = ttk.Label(frame, text=message, anchor="center", font=("Microsoft YaHei UI", 10))
        self.label.pack(pady=(0, 12))

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=380)
        self.progress.pack()
        self.progress.start(15)

        self.detail = ttk.Label(frame, text="", foreground="#888", font=("Microsoft YaHei UI", 9))
        self.detail.pack(pady=(8, 0))

        if self._cancellable:
            self._cancel_btn = ttk.Button(frame, text="取消", command=self._on_cancel)
            self._cancel_btn.pack(pady=(10, 0))
            # 点 X 关闭按钮也触发取消
            self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    @property
    def cancelled(self):
        return self._cancelled

    def _on_cancel(self):
        self._cancelled = True
        if self.winfo_exists():
            self.label.config(text="正在取消，请稍候...")
            self._cancel_btn.config(state="disabled")

    def update_message(self, message):
        self.after(0, self._set_text, self.label, message)

    def update_detail(self, text):
        self.after(0, self._set_text, self.detail, text)

    def _set_text(self, widget, text):
        if self.winfo_exists():
            widget.config(text=text)

    def close(self):
        if self.winfo_exists():
            self.progress.stop()
            self.grab_release()
            self.destroy()


class CheckableTreeview(ttk.Treeview):
    """带复选框的 Treeview。第一列为勾选框。"""

    def __init__(self, master, columns, **kwargs):
        # 始终插入 checkbox 列
        all_columns = ["__check__"] + list(columns)
        display_columns = list(columns)

        super().__init__(master, columns=all_columns, show="headings", **kwargs)

        self.heading("__check__", text="选择", anchor="center")
        self.column("__check__", width=50, minwidth=50, anchor="center", stretch=False)

        for col in columns:
            self.heading(col, text=col)
            self.column(col, width=100)

        self._checked = set()
        self.bind("<Button-1>", self._on_click)

        # 行交替颜色
        self.tag_configure("checked", background="#1a3a2a")
        self.tag_configure("unchecked", background="")

    def insert_row(self, values, checked=False, iid=None, **kwargs):
        """插入一行，values 对应非 checkbox 列。"""
        tag = "checked" if checked else "unchecked"
        check_mark = "☑" if checked else "☐"
        all_values = [check_mark] + list(values)
        item = super().insert("", tk.END, iid=iid, values=all_values, tags=(tag,), **kwargs)
        if checked:
            self._checked.add(item)
        return item

    def _on_click(self, event):
        region = self.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.identify_column(event.x)
        if col != "#1":  # 不是 checkbox 列
            return
        item = self.identify_row(event.y)
        if not item:
            return
        self.toggle(item)

    def toggle(self, item):
        if item in self._checked:
            self._checked.discard(item)
            vals = list(self.item(item, "values"))
            vals[0] = "☐"
            self.item(item, values=vals, tags=("unchecked",))
        else:
            self._checked.add(item)
            vals = list(self.item(item, "values"))
            vals[0] = "☑"
            self.item(item, values=vals, tags=("checked",))

    def check_all(self):
        for item in self.get_children():
            if item not in self._checked:
                self.toggle(item)

    def uncheck_all(self):
        for item in list(self._checked):
            self.toggle(item)

    def get_checked(self):
        return list(self._checked)

    def remove_item(self, item):
        """安全删除一行，同步清理 _checked 集合。"""
        self._checked.discard(item)
        self.delete(item)

    def get_checked_values(self):
        """返回已勾选行的原始值列表（不含 checkbox 列）。"""
        result = []
        for item in self._checked:
            vals = self.item(item, "values")
            result.append(vals[1:])  # 跳过 checkbox 列
        return result


def make_section(parent, title):
    """创建一个带标题的分组框，返回内部 Frame。"""
    lf = ttk.Labelframe(parent, text=f"  {title}  ", style="Section.TLabelframe")
    inner = ttk.Frame(lf)
    inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    return lf, inner
