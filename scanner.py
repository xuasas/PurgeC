"""扫描引擎：注册表读取、AppData 残留检测、文件夹大小统计。"""

import os
import re
import winreg


# ---------- 注册表：已安装程序 ----------

_UNINSTALL_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
]

_KB_RE = re.compile(r"KB\d{6,}", re.IGNORECASE)


def get_installed_programs():
    """返回已安装程序列表，每项为 dict: {name, install_location, publisher}。"""
    programs = []
    seen = set()

    for hive, subkey in _UNINSTALL_KEYS:
        try:
            key = winreg.OpenKey(hive, subkey)
        except OSError:
            continue

        i = 0
        while True:
            try:
                sub = winreg.EnumKey(key, i)
            except OSError:
                break
            i += 1

            try:
                subkey_handle = winreg.OpenKey(key, sub)
                name = _query_value(subkey_handle, "DisplayName")
                if not name:
                    continue
                # 跳过 Windows 更新补丁
                if _KB_RE.search(name):
                    continue
                if name in seen:
                    continue
                seen.add(name)

                install_loc = _query_value(subkey_handle, "InstallLocation") or ""
                publisher = _query_value(subkey_handle, "Publisher") or ""
                programs.append({
                    "name": name,
                    "install_location": install_loc,
                    "publisher": publisher,
                })
            except OSError:
                continue
            finally:
                try:
                    winreg.CloseKey(subkey_handle)
                except Exception:
                    pass

        winreg.CloseKey(key)

    return programs


def _query_value(key, value_name):
    try:
        val, _ = winreg.QueryValueEx(key, value_name)
        return val.strip() if isinstance(val, str) else val
    except OSError:
        return None


# ---------- AppData 残留扫描 ----------

def _normalize(name):
    """去除空格、版本号等干扰项，用于模糊匹配。"""
    name = name.lower()
    # 去掉常见版本号模式
    name = re.sub(r"\s*v?\d+(\.\d+)*", "", name)
    name = re.sub(r"[\s\-_]+", "", name)
    return name


def _find_exact_program(item_name, programs):
    """仅返回可靠的完全名称关联，避免把“最相似”的程序误显示出来。"""
    item_norm = _normalize(item_name)
    if not item_norm:
        return None
    for program in programs:
        if item_norm == _normalize(program["name"]):
            return program
    return None


def get_system_cleanup_paths():
    """返回适合纳入垃圾扫描的系统临时与诊断目录。"""
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    return [
        ("系统临时", os.path.join(system_root, "Temp")),
        ("系统崩溃转储", os.path.join(system_root, "Minidump")),
        ("内核诊断报告", os.path.join(system_root, "LiveKernelReports")),
        ("Windows 错误报告", os.path.join(
            os.environ.get("PROGRAMDATA", r"C:\ProgramData"), "Microsoft", "Windows", "WER"
        )),
    ]


def scan_appdata_leftovers(programs=None, scan_local=True, scan_roaming=True, extra_paths=None):
    """扫描 AppData 和额外目录的顶层文件、文件夹，交由用户审阅后清理。

    AppData 数据不等于垃圾，因此不再依靠模糊名称猜测“残留”。所有项目
    都会显示；仅明确的缓存/诊断文件标为低风险，其余保持可选但不预勾选。
    """
    if programs is None:
        programs = get_installed_programs()

    low_risk_names = {
        "cache", "code cache", "gpu cache", "shadercache", "shader cache",
        "crashdumps", "crash dumps", "temp", "tmp", "npm-cache",
        "pip-cache", "logs", "log",
    }
    low_risk_extensions = {".tmp", ".temp", ".dmp", ".mdmp", ".log", ".etl"}

    appdata_local = os.environ.get("LOCALAPPDATA", "")
    appdata_roaming = os.environ.get("APPDATA", "")

    scan_dirs = []
    if scan_local and appdata_local:
        scan_dirs.append(("Local", appdata_local))
    if scan_roaming and appdata_roaming:
        scan_dirs.append(("Roaming", appdata_roaming))
    for label, path in extra_paths or []:
        if path:
            scan_dirs.append((label, path))

    results = []

    for label, base in scan_dirs:
        if not os.path.isdir(base):
            continue
        try:
            entries = list(os.scandir(base))
        except OSError:
            continue

        for entry in entries:
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
                if not is_dir and not entry.is_file(follow_symlinks=False):
                    continue
                stat = entry.stat(follow_symlinks=False)
            except OSError:
                continue

            name_lower = entry.name.lower()
            extension = os.path.splitext(entry.name)[1].lower()
            program = _find_exact_program(entry.name, programs)
            is_low_risk = name_lower in low_risk_names or extension in low_risk_extensions

            if is_low_risk:
                category, risk, reason = "缓存 / 诊断文件", "低", "临时文件、缓存或崩溃诊断文件"
            elif program and program.get("install_location") and not os.path.isdir(program["install_location"]):
                category, risk, reason = "疑似卸载残留", "中", "程序名称完全匹配，且登记的安装目录不存在"
            elif program:
                category, risk, reason = "已安装程序数据", "高", "程序名称完全匹配；删除可能丢失配置或数据"
            else:
                category, risk, reason = "未确认应用数据", "高", "未自动判定为垃圾；请确认内容后再删除"

            size = get_folder_size(entry.path) if is_dir else stat.st_size
            results.append({
                "folder_name": entry.name,
                "path": entry.path,
                "size": size,
                "matched_program": program["name"] if program else "",
                "appdata_type": label,
                "item_type": "文件夹" if is_dir else "文件",
                "category": category,
                "risk": risk,
                "reason": reason,
            })

    # 按大小降序
    results.sort(key=lambda x: x["size"], reverse=True)
    return results


# ---------- 文件夹大小 ----------

_size_cache = {}


def get_folder_size(path):
    """递归计算文件夹大小（字节），带缓存和错误容忍。"""
    if path in _size_cache:
        return _size_cache[path]

    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += get_folder_size(entry.path)
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass

    _size_cache[path] = total
    return total


def clear_size_cache():
    _size_cache.clear()


# ---------- 大文件夹扫描 ----------

_SYSTEM_EXCLUDE = {
    "windows", "program files", "program files (x86)", "programdata",
    "$recycle.bin", "system volume information", "recovery",
    "perflogs", "intel", "amd", "nvidia",
}


def scan_large_folders(root="C:\\", top_n=50, max_depth=3, progress_callback=None):
    """扫描指定根目录下的大文件夹。

    返回列表 [{path, name, size, depth}, ...] 按大小降序。
    progress_callback(current_path) 可选回调。
    """
    results = []
    _walk_dirs(root, results, depth=0, max_depth=max_depth, progress_callback=progress_callback)
    results.sort(key=lambda x: x["size"], reverse=True)
    return results[:top_n]


def _walk_dirs(path, results, depth, max_depth, progress_callback):
    if depth > max_depth:
        return

    try:
        with os.scandir(path) as it:
            for entry in it:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if entry.name.lower() in _SYSTEM_EXCLUDE and depth == 0:
                    continue
                try:
                    size = get_folder_size(entry.path)
                    results.append({
                        "path": entry.path,
                        "name": entry.name,
                        "size": size,
                        "depth": depth,
                    })
                    if progress_callback:
                        progress_callback(entry.path)

                    if depth < max_depth:
                        _walk_dirs(entry.path, results, depth + 1, max_depth, progress_callback)
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass


# ---------- 临时文件扫描 ----------

_TEMP_PATHS = [
    os.environ.get("TEMP", ""),
    os.environ.get("TMP", ""),
    os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp"),
]


def scan_temp_files():
    """扫描临时文件目录，返回 [{path, size, modified}] 列表。"""
    results = []
    seen_paths = set()

    for temp_dir in _TEMP_PATHS:
        if not temp_dir or not os.path.isdir(temp_dir):
            continue
        try:
            with os.scandir(temp_dir) as it:
                for entry in it:
                    if entry.path in seen_paths:
                        continue
                    seen_paths.add(entry.path)
                    try:
                        stat = entry.stat(follow_symlinks=False)
                        if entry.is_file(follow_symlinks=False):
                            results.append({
                                "path": entry.path,
                                "name": entry.name,
                                "size": stat.st_size,
                                "modified": stat.st_mtime,
                                "is_dir": False,
                            })
                        elif entry.is_dir(follow_symlinks=False):
                            size = get_folder_size(entry.path)
                            results.append({
                                "path": entry.path,
                                "name": entry.name,
                                "size": size,
                                "modified": stat.st_mtime,
                                "is_dir": True,
                            })
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            continue

    results.sort(key=lambda x: x["size"], reverse=True)
    return results
