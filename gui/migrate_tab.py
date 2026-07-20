"""符号链接迁移 Tab：扫描大文件夹，迁移到其他盘。"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from migrate import scan_migrate_candidates, migrate_to_symlink, restore_from_symlink, list_existing_symlinks
from gui.widgets import format_size, ProgressDialog, CheckableTreeview


class MigrateTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._candidates = []
        self._build_ui()
        self.after(0, self._refresh_symlinks)

    def _build_ui(self):
        # ---- 顶部说明 ----
        desc = ttk.Label(
            self,
            text="仅迁移你勾选的 AppData 文件夹。目标盘会建立 PurgeC-Migrated 分类目录，原路径保留目录链接。迁移前请退出相关软件。",
            foreground="#888",
            font=("Microsoft YaHei UI", 9),
        )
        desc.pack(fill=tk.X, padx=16, pady=(14, 2))

        # ---- 扫描控制 ----
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, padx=16, pady=(6, 6))

        ttk.Label(ctrl, text="最小大小 (MB):", font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        self.var_min_size = tk.IntVar(value=100)
        ttk.Spinbox(ctrl, from_=10, to=10000, textvariable=self.var_min_size, width=8).pack(side=tk.LEFT, padx=(8, 4))

        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=2)
        ttk.Button(ctrl, text="扫描可迁移文件夹", command=self._start_scan).pack(side=tk.LEFT, padx=2)

        # ---- Notebook 子 Tab ----
        sub_notebook = ttk.Notebook(self)
        sub_notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)

        # 子 Tab 1: 可迁移项
        migrate_frame = ttk.Frame(sub_notebook)
        sub_notebook.add(migrate_frame, text="  可迁移文件夹  ")

        tree_frame = ttk.Frame(migrate_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("path", "size", "type")
        self.tree = CheckableTreeview(tree_frame, columns=columns, height=14)

        self.tree.heading("path", text="文件夹路径")
        self.tree.heading("size", text="大小")
        self.tree.heading("type", text="类型")

        self.tree.column("path", width=450)
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("type", width=60, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 子 Tab 2: 已有符号链接
        symlink_frame = ttk.Frame(sub_notebook)
        sub_notebook.add(symlink_frame, text="  已有符号链接  ")

        sym_tree_frame = ttk.Frame(symlink_frame)
        sym_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        sym_columns = ("link_path", "real_path", "type", "status", "time")
        self.sym_tree = ttk.Treeview(sym_tree_frame, columns=sym_columns, show="headings", height=14)

        self.sym_tree.heading("link_path", text="符号链接位置")
        self.sym_tree.heading("real_path", text="实际路径")
        self.sym_tree.heading("type", text="类型")
        self.sym_tree.heading("status", text="状态")
        self.sym_tree.heading("time", text="迁移时间")

        self.sym_tree.column("link_path", width=250)
        self.sym_tree.column("real_path", width=250)
        self.sym_tree.column("type", width=50, anchor="center")
        self.sym_tree.column("status", width=70, anchor="center")
        self.sym_tree.column("time", width=130, anchor="center")

        sym_scroll = ttk.Scrollbar(sym_tree_frame, orient=tk.VERTICAL, command=self.sym_tree.yview)
        self.sym_tree.configure(yscrollcommand=sym_scroll.set)
        self.sym_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sym_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.sym_tree.tag_configure("normal", foreground="#65c466")
        self.sym_tree.tag_configure("warning", foreground="#d89b39")
        self.sym_tree.tag_configure("external", foreground="#888")

        sym_btn_frame = ttk.Frame(symlink_frame)
        sym_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(sym_btn_frame, text="刷新", command=self._refresh_symlinks).pack(side=tk.LEFT)
        ttk.Button(sym_btn_frame, text="还原选中项", command=self._restore_symlink).pack(side=tk.LEFT, padx=10)

        # ---- 底部操作栏 ----
        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X, padx=16, pady=(4, 12))

        self.lbl_summary = ttk.Label(bottom, text="未扫描", foreground="#888")
        self.lbl_summary.pack(side=tk.LEFT)

        ttk.Button(bottom, text="迁移选中项到...", command=self._migrate_selected).pack(side=tk.RIGHT)

    def _start_scan(self):
        try:
            min_mb = self.var_min_size.get()
        except tk.TclError:
            messagebox.showerror("输入错误", "最小大小必须是有效整数。")
            return
        dlg = ProgressDialog(self, title="扫描中", message="正在扫描 AppData 大文件夹...")

        def run():
            results = scan_migrate_candidates(min_size_mb=min_mb)
            symlinks = list_existing_symlinks()
            self.after(0, lambda: self._on_scan_done(results, symlinks, dlg))

        threading.Thread(target=run, daemon=True).start()

    def _on_scan_done(self, results, symlinks, dlg):
        dlg.close()
        self._candidates = results

        # 填充可迁移列表
        for item in list(self.tree.get_children()):
            self.tree.remove_item(item)

        for r in results:
            self.tree.insert_row(
                values=(r["path"], format_size(r["size"]), r["appdata_type"]),
                checked=False,
            )

        total = sum(r["size"] for r in results)
        self.lbl_summary.config(
            text=f"找到 {len(results)} 个可迁移文件夹  |  总大小: {format_size(total)}"
        )

        # 填充已有符号链接
        self._fill_symlinks(symlinks)

    def _refresh_symlinks(self):
        symlinks = list_existing_symlinks()
        self._fill_symlinks(symlinks)
        managed = sum(1 for item in symlinks if item.get("managed"))
        if managed:
            self.lbl_summary.config(text=f"已加载 {managed} 条迁移记录；可在“已有符号链接”中查看状态")

    def _fill_symlinks(self, symlinks):
        for item in self.sym_tree.get_children():
            self.sym_tree.delete(item)
        for s in symlinks:
            status = s.get("status", "未知")
            if status == "正常":
                tags = ("normal",)
            elif s.get("managed"):
                tags = ("warning",)
            else:
                tags = ("external",)
            self.sym_tree.insert("", tk.END, values=(
                s["link_path"], s["real_path"], s.get("appdata_type", ""), status,
                s.get("time", "")
            ), tags=tags)

    def _migrate_selected(self):
        checked = self.tree.get_checked()
        if not checked:
            messagebox.showinfo("提示", "请先勾选要迁移的文件夹")
            return

        # 选择目标根目录
        target_root = filedialog.askdirectory(title="选择其他分区中的目标目录")
        if not target_root:
            return

        paths = []
        for item in checked:
            vals = self.tree.item(item, "values")
            paths.append(vals[1])  # path 列

        confirm = messagebox.askyesno(
            "确认迁移",
            f"将 {len(paths)} 个文件夹迁移到:\n{target_root}\\PurgeC-Migrated\\…\n\n"
            f"原位置将创建目录链接。若软件仍在运行，个别项目可能会失败；失败项目不会被覆盖。\n\n"
            f"确定继续？"
        )
        if not confirm:
            return

        dlg = ProgressDialog(self, title="迁移中", message="正在迁移...")

        def run():
            results = []
            for p in paths:
                ok, msg = migrate_to_symlink(
                    p, target_root,
                    progress_callback=lambda t: dlg.update_detail(t),
                )
                results.append((p, ok, msg))
            self.after(0, lambda: self._on_migrate_done(results, dlg))

        threading.Thread(target=run, daemon=True).start()

    def _on_migrate_done(self, results, dlg):
        dlg.close()

        success = []
        failed = []
        for path, ok, msg in results:
            if ok:
                success.append(path)
            else:
                failed.append((path, msg))

        # 从列表中移除成功的项
        for item in list(self.tree.get_children()):
            vals = self.tree.item(item, "values")
            if vals[1] in success:
                self.tree.remove_item(item)

        # 刷新符号链接列表
        self._refresh_symlinks()

        msg = f"成功迁移 {len(success)} 项"
        if failed:
            msg += f"\n失败 {len(failed)} 项:"
            for p, e in failed[:5]:
                msg += f"\n  {os.path.basename(p)}: {e}"
        messagebox.showinfo("迁移完成", msg)

    def _restore_symlink(self):
        sel = self.sym_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要还原的符号链接")
            return

        live_items = []
        unavailable = []
        for item in sel:
            vals = self.sym_tree.item(item, "values")
            link_path = vals[0]
            status = vals[3] if len(vals) > 3 else ""
            if status == "正常":
                live_items.append(link_path)
            else:
                unavailable.append((os.path.basename(link_path), status))

        if not live_items:
            messagebox.showwarning(
                "无法还原", "只有状态为“正常”的 PurgeC 迁移链接可以还原。\n\n"
                + "\n".join(f"{name}：{status}" for name, status in unavailable[:5]),
            )
            return

        confirm = messagebox.askyesno(
            "确认还原",
            f"将 {len(live_items)} 个符号链接还原为真实文件夹:\n\n"
            + "\n".join(live_items) + "\n\n确定继续？"
        )
        if not confirm:
            return

        dlg = ProgressDialog(self, title="还原中", message="正在还原...")

        def run():
            results = []
            for link_path in live_items:
                ok, msg = restore_from_symlink(link_path, progress_callback=lambda t: dlg.update_detail(t))
                results.append((link_path, ok, msg))
            self.after(0, lambda: self._on_restore_done(results, dlg))

        threading.Thread(target=run, daemon=True).start()

    def _on_restore_done(self, results, dlg):
        dlg.close()

        success = [p for p, ok, _ in results if ok]
        failed = [(p, msg) for p, ok, msg in results if not ok]

        # 移除成功的行
        for item in self.sym_tree.get_children():
            vals = self.sym_tree.item(item, "values")
            if vals[0] in success:
                self.sym_tree.delete(item)

        msg = f"成功还原 {len(success)} 项"
        if failed:
            msg += f"\n失败 {len(failed)} 项"
        messagebox.showinfo("还原完成", msg)
