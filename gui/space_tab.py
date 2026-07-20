"""空间分析 Tab：文件夹大小树形图 + 柱状图。"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog

from scanner import scan_large_folders, get_folder_size, clear_size_cache
from gui.widgets import format_size, ProgressDialog


class SpaceTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        # ---- 顶部控制 ----
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, padx=16, pady=(14, 6))

        ttk.Label(ctrl, text="扫描路径:", font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        self.var_path = tk.StringVar(value="C:\\")
        ttk.Entry(ctrl, textvariable=self.var_path, width=28).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Button(ctrl, text="浏览...", command=self._browse).pack(side=tk.LEFT, padx=2)

        ttk.Separator(ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=2)

        ttk.Label(ctrl, text="深度:").pack(side=tk.LEFT)
        self.var_depth = tk.IntVar(value=2)
        ttk.Spinbox(ctrl, from_=1, to=5, textvariable=self.var_depth, width=4).pack(side=tk.LEFT, padx=4)

        ttk.Button(ctrl, text="分析", command=self._start_analyze).pack(side=tk.LEFT, padx=(12, 2))

        # ---- 主内容区 ----
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)

        # 左侧：树形图
        left = ttk.Frame(paned)
        paned.add(left, weight=3)

        ttk.Label(left, text="目录树", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        tree_container = ttk.Frame(left)
        tree_container.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        columns = ("size", "pct")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="tree headings")
        self.tree.heading("#0", text="文件夹")
        self.tree.heading("size", text="大小")
        self.tree.heading("pct", text="占比")
        self.tree.column("#0", width=300)
        self.tree.column("size", width=100, anchor="e")
        self.tree.column("pct", width=60, anchor="e")

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self._on_double_click)

        # 右侧：柱状图
        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        ttk.Label(right, text="Top 10 最大文件夹", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        self.canvas = tk.Canvas(right, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=(4, 0))

    def _browse(self):
        path = filedialog.askdirectory(initialdir=self.var_path.get())
        if path:
            self.var_path.set(path)

    def _start_analyze(self):
        root_path = os.path.abspath(self.var_path.get().strip())
        if not os.path.isdir(root_path):
            from tkinter import messagebox
            messagebox.showerror("路径无效", "请选择一个存在的文件夹。")
            return
        try:
            max_depth = self.var_depth.get()
        except tk.TclError:
            from tkinter import messagebox
            messagebox.showerror("输入错误", "深度必须是有效整数。")
            return
        clear_size_cache()

        dlg = ProgressDialog(self, title="分析中", message="正在统计文件夹大小...")

        def progress_cb(current_path):
            dlg.update_detail(current_path)

        def run():
            results = scan_large_folders(
                root=root_path, top_n=50, max_depth=max_depth,
                progress_callback=progress_cb,
            )
            self.after(0, lambda: self._on_analyze_done(results, root_path, dlg))

        threading.Thread(target=run, daemon=True).start()

    def _on_analyze_done(self, results, root_path, dlg):
        dlg.close()

        # 清空旧数据
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not results:
            return

        total_root = sum(r["size"] for r in results if r["depth"] == 0) or 1

        # 构建树
        path_to_item = {}

        # 根节点
        root_total = get_folder_size(root_path) if os.path.isdir(root_path) else total_root
        root_item = self.tree.insert("", tk.END, text=root_path,
                                      values=(format_size(root_total), "100%"))
        path_to_item[root_path.rstrip("\\/")] = root_item

        for r in results:
            parent_path = os.path.dirname(r["path"]).rstrip("\\/")
            parent_item = path_to_item.get(parent_path, root_item)
            pct = r["size"] / root_total * 100 if root_total > 0 else 0

            item = self.tree.insert(
                parent_item, tk.END,
                text=r["name"],
                values=(format_size(r["size"]), f"{pct:.1f}%"),
            )
            path_to_item[r["path"].rstrip("\\/")] = item

        # 展开根节点
        self.tree.item(root_item, open=True)

        # 绘制柱状图
        self._draw_bar_chart(results[:10], root_total)

    def _draw_bar_chart(self, items, total):
        self.canvas.delete("all")
        if not items:
            return

        self.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            self.after(100, lambda: self._draw_bar_chart(items, total))
            return

        margin_left = 8
        margin_right = 8
        margin_top = 8
        bar_height = max(22, (ch - margin_top - 8) // len(items) - 6)
        gap = 6
        max_width = cw - margin_left - margin_right

        colors = [
            "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7", "#d946ef",
            "#ec4899", "#f43f5e", "#ef4444", "#f97316", "#eab308",
        ]

        max_size = items[0]["size"] if items else 1

        for i, item in enumerate(items):
            y = margin_top + i * (bar_height + gap)
            bar_w = int((item["size"] / max_size) * (max_width - 130)) if max_size > 0 else 0
            bar_w = max(bar_w, 2)

            color = colors[i % len(colors)]
            # 柱状条
            self.canvas.create_rectangle(
                80, y, 80 + bar_w, y + bar_height,
                fill=color, outline="",
            )

            # 名称（截断）
            name = item["name"]
            if len(name) > 10:
                name = name[:9] + "…"
            self.canvas.create_text(76, y + bar_height // 2,
                                    text=name, anchor="e", font=("Microsoft YaHei UI", 9))

            # 大小
            self.canvas.create_text(84 + bar_w, y + bar_height // 2,
                                    text=format_size(item["size"]), anchor="w", font=("Microsoft YaHei UI", 8))

    def _on_double_click(self, event):
        item = self.tree.focus()
        if item:
            self.tree.item(item, open=not self.tree.item(item, "open"))
