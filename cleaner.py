"""安全清理模块：将文件/文件夹移到回收站，带操作日志。"""

import logging
import os
import threading

logger = logging.getLogger("purgec")
logger.setLevel(logging.INFO)

_log_path = os.path.join(os.path.dirname(__file__), "purgec.log")
if not logger.handlers:
    _handler = logging.FileHandler(_log_path, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_handler)

# 单个文件删除操作的超时时间（秒），超时则视为文件被占用，自动跳过
_SEND2TRASH_TIMEOUT = 8


def _is_file_in_use(file_path):
    """通过尝试以独占模式打开文件，快速判断文件是否正在被其他进程使用。

    对于目录则返回 False（无法用此方法可靠检测）。
    返回 True 表示文件很可能正被占用，应跳过。
    """
    if not os.path.isfile(file_path):
        return False
    try:
        # 尝试以独占读写模式打开，如果文件被其他进程锁定则会失败
        with open(file_path, "r+b") as fh:
            pass
        # 如果独占打开成功，再试一下 send2trash 是否会失败
        return False
    except (PermissionError, OSError):
        return True


def _safe_send2trash_one(path):
    """在子线程中调用 send2trash，超时则跳过该文件。

    Returns:
        (success: bool, error: Exception | None)
    """
    from send2trash import send2trash

    result = {"ok": False, "error": None}

    def _run():
        try:
            send2trash(path)
            result["ok"] = True
        except Exception as exc:
            result["error"] = exc

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=_SEND2TRASH_TIMEOUT)

    if t.is_alive():
        # 超时 —— 文件很可能被其他进程占用，跳过
        return False, OSError(
            f"操作超时（{_SEND2TRASH_TIMEOUT} 秒），文件可能正在被其他程序使用"
        )

    if result["ok"]:
        return True, None
    return False, result["error"]


def send_to_trash(paths, progress_callback=None, cancel_check=None):
    """将路径列表中的文件/文件夹移到回收站。

    遇到正被其他进程占用的文件会自动跳过，不会卡住整个清理流程。

    Args:
        paths: 要删除的路径列表。
        progress_callback: fn(current_index, total, current_path) 可选回调。
        cancel_check: fn() -> bool 可选回调，返回 True 时中止后续删除。

    Returns:
        (success_count, failed_list) — failed_list 为 [(path, error_msg), ...]
    """
    try:
        from send2trash import send2trash  # noqa: F401  # 仅校验是否已安装
    except ImportError:
        raise RuntimeError("请先安装 send2trash: pip install send2trash")

    total = len(paths)
    success = 0
    failed = []

    for i, path in enumerate(paths):
        # 用户手动取消
        if cancel_check and cancel_check():
            logger.warning("用户取消清理，已跳过剩余 %d 项", total - i)
            break

        if progress_callback:
            progress_callback(i, total, path)

        # ---- 快速预检：文件是否被占用 ----
        if _is_file_in_use(path):
            msg = "文件正被其他程序使用，已跳过"
            failed.append((path, msg))
            logger.warning("跳过占用文件: %s", path)
            continue

        # ---- 带超时的安全删除 ----
        ok, error = _safe_send2trash_one(path)

        if ok:
            success += 1
            logger.info("已移到回收站: %s", path)
        else:
            err_msg = str(error) if error else "未知错误"
            failed.append((path, err_msg))
            logger.error("移到回收站失败: %s — %s", path, err_msg)

    return success, failed
