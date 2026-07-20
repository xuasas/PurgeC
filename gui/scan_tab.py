"""残留扫描 Tab：扫描 AppData 中的残留文件夹。"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from scanner import scan_appdata_leftovers, get_installed_programs, get_system_cleanup_paths
from cleaner import send_to_trash
from gui.widgets import format_size, ProgressDialog, CheckableTreeview


class ScanTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._scan_results = []
        self._build_ui()

    def _build_ui(self):
        ttk.Label(
            self,
            text="可扫描 AppData、系统临时/诊断目录及自选目录。所有结果均可手动勾选；只有低风险缓存适合优先清理。",
            foreground="#c98b2e",
            wraplength=980,
        ).pack(fill=tk.X, padx=16, pady=(12, 0))

        # ---- 顶部控制栏 ----
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, padx=16, pady=(8, 6))

        # 扫描范围
        ttk.Label(ctrl, text="扫描范围:", font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)

        self.var_local = tk.BooleanVar(value=True)
        self.var_roaming = tk.BooleanVar(value=True)
        self.var_system = tk.BooleanVar(value=True)
        self.var_extra_path = tk.StringVar()
        ttk.Checkbutton(ctrl, text="Local", variable=self.var_local).pack(side=tk.LEFT, padx=(12, 4))
        ttk.Checkbutton(ctrl, text="Roaming", variable=self.var_roaming).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(ctrl, text="系统临时 / 诊断", variable=self.var_system).pack(side=tk.LEFT, padx=(10, 4))
        ttk.Button(ctrl, text="选择其他目录...", command=self._browse_extra_path).pack(side=tk.LEFT, padx=(8, 2))
        self.extra_path_label = ttk.Label(ctrl, text="未选择", foreground="#888", width=18)
        self.extra_path_label.pack(side=tk.LEFT, padx=(2, 4))

        # 操作按钮
        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=2)
        ttk.Button(ctrl, text="开始扫描", command=self._start_scan).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="全选（含高风险）", command=self._check_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="反选", command=self._invert_check).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="取消全选", command=self._uncheck_all).pack(side=tk.LEFT, padx=2)

        # ---- 表格 ----
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)

        columns = ("program", "path", "size", "category", "risk", "type")
        self.tree = CheckableTreeview(tree_frame, columns=columns, height=18)

        self.tree.heading("program", text="可靠关联程序")
        self.tree.heading("path", text="文件 / 文件夹路径")
        self.tree.heading("size", text="大小")
        self.tree.heading("category", text="分类")
        self.tree.heading("risk", text="风险")
        self.tree.heading("type", text="类型")

        self.tree.column("program", width=150)
        self.tree.column("path", width=370)
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("category", width=130, anchor="center")
        self.tree.column("risk", width=55, anchor="center")
        self.tree.column("type", width=95, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._show_selected_reason)

        # 右键菜单
        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="打开文件夹位置", command=self._open_folder)
        self._ctx_menu.add_command(label="从列表中移除", command=self._remove_selected)
        self.tree.bind("<Button-3>", self._show_context_menu)

        self.lbl_reason = ttk.Label(
            self, text="选择一项可查看分类依据。", foreground="#888", anchor="w"
        )
        self.lbl_reason.pack(fill=tk.X, padx=16, pady=(0, 2))

        # ---- 底部汇总 + 操作 ----
        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X, padx=16, pady=(4, 12))

        self.lbl_summary = ttk.Label(bottom, text="未扫描", foreground="#888")
        self.lbl_summary.pack(side=tk.LEFT)

        ttk.Button(bottom, text="清理选中项", command=self._clean_selected).pack(side=tk.RIGHT)

    def _start_scan(self):
        dlg = ProgressDialog(self, title="扫描中", message="正在读取已安装程序列表...")
        self.update_idletasks()

        def run():
            programs = get_installed_programs()
            dlg.update_message(f"已找到 {len(programs)} 个程序，正在扫描 AppData...")
            extra_paths = get_system_cleanup_paths() if self.var_system.get() else []
            if self.var_extra_path.get():
                extra_paths.append(("自选目录", self.var_extra_path.get()))

            results = scan_appdata_leftovers(
                programs=programs,
                scan_local=self.var_local.get(),
                scan_roaming=self.var_roaming.get(),
                extra_paths=extra_paths,
            )

            self.after(0, lambda: self._on_scan_done(results, dlg))

        threading.Thread(target=run, daemon=True).start()

    def _on_scan_done(self, results, dlg):
        dlg.close()
        self._scan_results = results
        self._populate_tree()
        total_size = sum(r["size"] for r in results)
        self.lbl_summary.config(
            text=f"扫描到 {len(results)} 项可审阅数据  |  总大小: {format_size(total_size)}"
        )

    def _browse_extra_path(self):
        path = filedialog.askdirectory(title="选择要扫描的额外目录", initialdir="C:\\")
        if path:
            self.var_extra_path.set(path)
            short_path = path if len(path) <= 24 else "…" + path[-23:]
            self.extra_path_label.config(text=short_path, foreground="#aaa")

    def _populate_tree(self):
        for item in list(self.tree.get_children()):
            self.tree.remove_item(item)

        for r in self._scan_results:
            self.tree.insert_row(
                values=(
                    r["matched_program"] or "未确认",
                    r["path"],
                    format_size(r["size"]),
                    r["category"],
                    r["risk"],
                    f"{r['appdata_type']} / {r['item_type']}",
                ),
                checked=False,
            )

    def _check_all(self):
        self.tree.check_all()

    def _uncheck_all(self):
        self.tree.uncheck_all()

    def _invert_check(self):
        for item in self.tree.get_children():
            self.tree.toggle(item)

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _show_selected_reason(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        path = self.tree.item(selected[0], "values")[2]
        record = next((item for item in self._scan_results if item["path"] == path), None)
        if record:
            self.lbl_reason.config(text=f"{record['category']}：{record['reason']}")

    def _open_folder(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        path = vals[2]  # path 列
        if os.path.isdir(path):
            os.startfile(path)
        elif os.path.isfile(path):
            os.startfile(os.path.dirname(path))

    def _remove_selected(self):
        sel = self.tree.selection()
        for item in sel:
            self.tree.remove_item(item)

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
            f"将以下 {len(paths)} 个项目移到回收站。应用数据可能导致软件丢失配置、缓存或登录状态。\n\n确定继续？\n\n"
            + "\n".join(paths[:10])
            + ("\n..." if len(paths) > 10 else ""),
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

        # 移除成功的行
        failed_paths = {path for path, _ in fail}
        for item in list(self.tree.get_checked()):
            values = self.tree.item(item, "values")
            if values[2] not in failed_paths:
                self.tree.remove_item(item)

        msg = f"成功清理 {ok} 项"
        if fail:
            msg += f"\n失败 {len(fail)} 项"
            for p, e in fail[:5]:
                msg += f"\n  {p}: {e}"
        messagebox.showinfo("清理完成", msg)
