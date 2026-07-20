"""主窗口：组合各 Tab 页。"""

import sv_ttk
import tkinter as tk
from tkinter import ttk

from gui.scan_tab import ScanTab
from gui.space_tab import SpaceTab
from gui.temp_tab import TempTab
from gui.migrate_tab import MigrateTab


class App(tk.Tk):
    def __init__(self, is_admin=False):
        super().__init__()
        self.is_admin = is_admin

        # ---- 启用 Sun Valley 主题 ----
        sv_ttk.set_theme("dark")

        self.title("PurgeC — C盘清理工具")
        self.geometry("1080x700")
        self.minsize(900, 560)

        # ---- 配置统一样式 ----
        # 使用微软雅黑，字号 10 作为全局默认，解决模糊问题
        default_font = ("Microsoft YaHei UI", 10)
        bold_font = ("Microsoft YaHei UI", 10, "bold")
        header_font = ("Microsoft YaHei UI", 20, "bold")
        small_font = ("Microsoft YaHei UI", 9)

        style = ttk.Style()
        # 全局默认字体
        style.configure(".", font=default_font)

        # Treeview 行高适配
        style.configure("Treeview", rowheight=28, font=default_font)
        style.configure("Treeview.Heading", font=bold_font)

        # 自定义样式
        style.configure("Header.TLabel", font=header_font)
        style.configure("Sub.TLabel", font=default_font)
        style.configure("Admin.Green.TLabel", foreground="#4caf50", font=small_font)
        style.configure("Admin.Gray.TLabel", foreground="#888", font=small_font)
        style.configure("Status.TLabel", foreground="#999", font=small_font)
        style.configure("Accent.TButton", font=bold_font)
        style.configure("Section.TLabelframe.Label", font=bold_font)

        # ---- 顶部标题栏 ----
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=16, pady=(12, 4))

        left = ttk.Frame(header)
        left.pack(side=tk.LEFT)

        ttk.Label(left, text="PurgeC", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(left, text="  释放空间，操作可追溯", style="Sub.TLabel").pack(side=tk.LEFT, pady=(6, 0))

        right = ttk.Frame(header)
        right.pack(side=tk.RIGHT)

        # 管理员状态
        if is_admin:
            ttk.Label(right, text="[管理员]", style="Admin.Green.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        else:
            ttk.Label(right, text="[普通权限]", style="Admin.Gray.TLabel").pack(side=tk.LEFT, padx=(0, 8))
            ttk.Button(right, text="管理员重启", command=self._elevate).pack(side=tk.LEFT)

        # 深色/浅色切换
        self._is_dark = True
        ttk.Button(right, text="主题切换", command=self._toggle_theme).pack(side=tk.LEFT, padx=(8, 0))

        # 关于
        ttk.Button(right, text="关于", command=self._show_about).pack(side=tk.LEFT, padx=(8, 0))

        # ---- 分割线 ----
        sep = ttk.Separator(self)
        sep.pack(fill=tk.X, padx=16)

        # ---- Notebook Tab ----
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 4))

        self.scan_tab = ScanTab(self.notebook)
        self.space_tab = SpaceTab(self.notebook)
        self.temp_tab = TempTab(self.notebook)
        self.migrate_tab = MigrateTab(self.notebook)

        self.notebook.add(self.scan_tab, text=" 残留扫描 ")
        self.notebook.add(self.space_tab, text=" 空间分析 ")
        self.notebook.add(self.temp_tab, text=" 临时文件 ")
        self.notebook.add(self.migrate_tab, text=" 应用数据迁移 ")

        # ---- 底部状态栏 ----
        status = ttk.Frame(self)
        status.pack(fill=tk.X, padx=16, pady=(0, 8))
        self.lbl_status = ttk.Label(status, text="就绪", style="Status.TLabel")
        self.lbl_status.pack(side=tk.LEFT)

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        sv_ttk.set_theme("dark" if self._is_dark else "light")

    def _elevate(self):
        from main import elevate
        elevate()

    def _show_about(self):
        dialog = tk.Toplevel(self)
        dialog.title("关于 PurgeC")
        dialog.geometry("500x285")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=24)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="PurgeC", font=("Microsoft YaHei UI", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="C 盘空间整理工具 · 本地运行 · 操作可追溯", foreground="#888").pack(anchor="w", pady=(2, 18))
        ttk.Label(
            frame,
            text="PurgeC 完全开源，可免费使用。\n如果你是通过付费购买获得它的，很可能被忽悠了；请谨慎核实出售方。",
            justify=tk.LEFT,
            wraplength=440,
        ).pack(anchor="w")
        ttk.Label(frame, text="作者：Github-Xuasas", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", pady=(18, 4))
        ttk.Label(frame, text="提示：清理或迁移前请退出相关软件，重要数据请先备份。", foreground="#c98b2e").pack(anchor="w")
        ttk.Button(frame, text="关闭", command=dialog.destroy).pack(anchor="e", pady=(14, 0))
