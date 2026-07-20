"""PurgeC — C盘清理工具入口。"""

import sys
import os
import ctypes

# ---- DPI 感知：必须在 tkinter 导入之前设置 ----
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def is_admin():
    """检查当前是否以管理员身份运行。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate():
    """请求 UAC 提升；同时兼容源码运行和 PyInstaller 打包运行。"""
    params = " ".join(f'"{a}"' for a in sys.argv if a != "--elevate")
    if getattr(sys, "frozen", False):
        executable, arguments = sys.executable, params
    else:
        executable, arguments = sys.executable, f'"{os.path.abspath(__file__)}" {params}'
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, arguments, None, 1)
    if result > 32:
        sys.exit(0)


def main():
    from gui.app import App

    admin = is_admin()
    app = App(is_admin=admin)
    app.mainloop()


if __name__ == "__main__":
    main()
