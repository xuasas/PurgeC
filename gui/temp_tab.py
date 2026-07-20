"""临时文件清理 Tab。"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from scanner import scan_temp_files
from cleaner import send_to_trash
from gui.widgets import format_size, ProgressDialog, CheckableTreeview


class TempTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._scan_results = []
        self._build_ui()

    def _build_ui(self):
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, padx=16, pady=(14, 6))

        ttk.Button(ctrl, text="扫描临时文件", command=self._start_scan).pack(side=tk.LEFT)
        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=2)
        ttk.Button(ctrl, text="全选", command=self.tree_check_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="取消全选", command=self.tree_uncheck_all).pack(side=tk.LEFT, padx=2)

        # 表格
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)

        columns = ("name", "path", "size", "type")
        self.tree = CheckableTreeview(tree_frame, columns=columns, height=18)

        self.tree.heading("name", text="名称")
        self.tree.heading("path", text="路径")
        self.tree.heading("size", text="大小")
        self.tree.heading("type", text="类型")

        self.tree.column("name", width=150)
        self.tree.column("path", width=400)
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("type", width=60, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部
        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X, padx=16, pady=(4, 12))

        self.lbl_summary = ttk.Label(bottom, text="未扫描", foreground="#888")
        self.lbl_summary.pack(side=tk.LEFT)

        ttk.Button(bottom, text="清理选中项", command=self._clean_selected).pack(side=tk.RIGHT)

    def tree_check_all(self):
        self.tree.check_all()

    def tree_uncheck_all(self):
        self.tree.uncheck_all()

    def _start_scan(self):
        dlg = ProgressDialog(self, title="扫描中", message="正在扫描临时文件...")

        def run():
            results = scan_temp_files()
            self.after(0, lambda: self._on_scan_done(results, dlg))

        threading.Thread(target=run, daemon=True).start()

    def _on_scan_done(self, results, dlg):
        dlg.close()
        self._scan_results = results

        for item in list(self.tree.get_children()):
            self.tree.remove_item(item)

        for r in results:
            self.tree.insert_row(
                values=(
                    r["name"],
                    r["path"],
                    format_size(r["size"]),
                    "文件夹" if r["is_dir"] else "文件",
                ),
                checked=True,  # 临时文件默认全选
            )

        total = sum(r["size"] for r in results)
        self.lbl_summary.config(
            text=f"共 {len(results)} 项  |  总大小: {format_size(total)}"
        )

    def _clean_selected(self):
        checked_items = self.tree.get_checked()
        if not checked_items:
            messagebox.showinfo("提示", "请先勾选要清理的项目")
            return

        paths = []
        for item in checked_items:
            vals = self.tree.item(item, "values")
            paths.append(vals[2])  # path 列

        confirm = messagebox.askyesno(
            "确认清理",
            f"将 {len(paths)} 个项目移到回收站，确定继续？"
        )
        if not confirm:
            return

        dlg = ProgressDialog(self, title="清理中", message="正在移动到回收站...", cancellable=True)

        def run():
            ok, fail = send_to_trash(paths, cancel_check=lambda: dlg.cancelled)
            self.after(0, lambda: self._on_clean_done(ok, fail, dlg))

        threading.Thread(target=run, daemon=True).start()

    def _on_clean_done(self, ok, fail, dlg):
        dlg.close()

        failed_paths = {path for path, _ in fail}
        for item in list(self.tree.get_checked()):
            values = self.tree.item(item, "values")
            if values[2] not in failed_paths:
                self.tree.remove_item(item)

        msg = f"成功清理 {ok} 项"
        if fail:
            msg += f"\n失败 {len(fail)} 项"
        messagebox.showinfo("清理完成", msg)
