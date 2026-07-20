"""安全迁移 AppData 文件夹，并在原位置创建目录链接。"""

import json
import os
import shutil
import subprocess
import time


_APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.dirname(__file__)), "PurgeC")
_HISTORY_PATH = os.path.join(_APP_DIR, "migrate_history.json")
_REPARSE_POINT = 0x400


def _load_history():
    try:
        with open(_HISTORY_PATH, encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_history(records):
    try:
        os.makedirs(_APP_DIR, exist_ok=True)
        temp_path = f"{_HISTORY_PATH}.tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(records, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, _HISTORY_PATH)
    except OSError:
        pass


def _add_history_record(name, link_path, real_path, appdata_type):
    link_key = _path_key(link_path)
    records = [r for r in _load_history() if _path_key(r.get("link_path", "")) != link_key]
    records.append({"name": name, "link_path": link_path, "real_path": real_path,
                    "appdata_type": appdata_type, "link_type": "junction",
                    "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    _save_history(records)


def _remove_history_record(link_path):
    link_key = _path_key(link_path)
    _save_history([r for r in _load_history() if _path_key(r.get("link_path", "")) != link_key])


def get_migration_history():
    return _load_history()


def _path_key(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(path))) if path else ""


def _get_history_record(link_path):
    link_key = _path_key(link_path)
    return next((record for record in _load_history()
                 if _path_key(record.get("link_path", "")) == link_key), None)


def _is_link(path):
    """同时识别 symlink 和 Windows junction（junction 不一定被 islink 识别）。"""
    try:
        return os.path.islink(path) or bool(getattr(os.lstat(path), "st_file_attributes", 0) & _REPARSE_POINT)
    except OSError:
        return False


def _link_target(path):
    try:
        target = os.readlink(path)
        if target.startswith("\\\\?\\") or target.startswith("\\??\\"):
            target = target[4:]
        return os.path.abspath(os.path.join(os.path.dirname(path), target))
    except OSError:
        return os.path.realpath(path)


def _appdata_type(path):
    local = os.path.normcase(os.path.abspath(os.environ.get("LOCALAPPDATA", "")))
    return "Local" if local and os.path.normcase(os.path.abspath(path)).startswith(local + os.sep) else "Roaming"


def scan_migrate_candidates(min_size_mb=100):
    """扫描 AppData 顶层可迁移目录；不跟随任何链接。"""
    from scanner import get_folder_size

    excluded = {"microsoft", "windows", "system", "packages", "temp"}
    results = []
    for label, base in (("Roaming", os.environ.get("APPDATA", "")),
                        ("Local", os.environ.get("LOCALAPPDATA", ""))):
        if not os.path.isdir(base):
            continue
        try:
            entries = list(os.scandir(base))
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False) or _is_link(entry.path):
                continue
            if any(word in entry.name.lower() for word in excluded):
                continue
            size = get_folder_size(entry.path)
            if size >= min_size_mb * 1024 * 1024:
                results.append({"name": entry.name, "path": entry.path, "size": size,
                                "appdata_type": label})
    return sorted(results, key=lambda item: item["size"], reverse=True)


def _create_directory_link(target, link):
    """优先使用 junction：无需开发者模式/UAC，且对旧软件兼容性更好。"""
    try:
        result = subprocess.run(
            ["cmd", "/d", "/s", "/c", f'mklink /J "{link}" "{target}"'],
            capture_output=True, text=True, encoding="mbcs", errors="replace", check=False,
        )
    except OSError as exc:
        raise OSError(f"无法启动 mklink：{exc}") from exc
    if result.returncode or not _is_link(link):
        detail = (result.stderr or result.stdout).strip()
        raise OSError(detail or "创建目录链接失败")


def _validate_paths(src_path, target_root):
    src_path = os.path.abspath(src_path)
    target_root = os.path.abspath(target_root)
    if not os.path.isdir(src_path) or _is_link(src_path):
        return None, "源路径不存在、不是目录，或已经是链接。"
    if not os.path.isdir(target_root):
        return None, "目标目录不存在。"
    if os.path.normcase(os.path.splitdrive(src_path)[0]) == os.path.normcase(os.path.splitdrive(target_root)[0]):
        return None, "目标必须位于与源目录不同的磁盘分区。"
    if os.path.commonpath([src_path, target_root]) == src_path:
        return None, "目标目录不能位于待迁移文件夹内。"
    return (src_path, target_root), ""


def migrate_to_symlink(src_path, target_root, progress_callback=None):
    """迁移一个已选目录。失败时尽力回滚，绝不覆盖目标中的已有数据。"""
    checked, error = _validate_paths(src_path, target_root)
    if not checked:
        return False, error
    src_path, target_root = checked
    folder_name = os.path.basename(src_path)
    category = _appdata_type(src_path)
    target_path = os.path.join(target_root, "PurgeC-Migrated", category, folder_name)
    if os.path.lexists(target_path):
        return False, f"目标已存在，未覆盖：{target_path}"

    from scanner import get_folder_size
    needed = get_folder_size(src_path)
    try:
        if shutil.disk_usage(target_root).free < needed:
            return False, "目标磁盘可用空间不足。"
    except OSError:
        return False, "无法读取目标磁盘剩余空间。"

    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        if progress_callback:
            progress_callback(f"正在移动 {folder_name}…")
        shutil.move(src_path, target_path)
        if progress_callback:
            progress_callback("正在创建目录链接…")
        _create_directory_link(target_path, src_path)
    except Exception as exc:
        if os.path.isdir(target_path) and not os.path.lexists(src_path):
            try:
                shutil.move(target_path, src_path)
                return False, f"迁移失败，已回滚：{exc}"
            except Exception as rollback_error:
                return False, f"迁移失败且回滚失败；数据仍在 {target_path}。原因：{rollback_error}"
        return False, f"迁移失败：{exc}"

    _add_history_record(folder_name, src_path, target_path, category)
    return True, f"迁移完成：{folder_name}"


def restore_from_symlink(link_path, progress_callback=None):
    """将 PurgeC 创建的目录链接还原为真实目录。"""
    link_path = os.path.abspath(link_path)
    record = _get_history_record(link_path)
    if not record:
        return False, "该链接不是由 PurgeC 创建，已拒绝还原以保护数据。"
    if not _is_link(link_path):
        return False, "该路径不是目录链接。"
    real_path = os.path.abspath(record.get("real_path", ""))
    actual_target = _link_target(link_path)
    if _path_key(actual_target) != _path_key(real_path):
        return False, "链接目标与迁移记录不一致，已拒绝还原以保护数据。"
    if not os.path.isdir(real_path) or os.path.normcase(real_path) == os.path.normcase(link_path):
        return False, "链接目标不存在或无法识别。"
    try:
        if progress_callback:
            progress_callback(f"正在移除链接 {os.path.basename(link_path)}…")
        os.rmdir(link_path)
        if progress_callback:
            progress_callback("正在移回文件夹…")
        shutil.move(real_path, link_path)
    except Exception as exc:
        # 删除链接后移动失败时，尽力恢复链接，避免应用看到空目录。
        if not os.path.lexists(link_path) and os.path.isdir(real_path):
            try:
                _create_directory_link(real_path, link_path)
            except Exception:
                pass
        return False, f"还原失败：{exc}"
    _remove_history_record(link_path)
    return True, f"已还原：{os.path.basename(link_path)}"


def list_existing_symlinks():
    """列出持久化的迁移记录，并校验链接和目标在重启后是否仍正常。"""
    history = _load_history()
    records_by_path = {_path_key(record.get("link_path", "")): record for record in history}
    results, live_paths = [], set()
    for label, base in (("Roaming", os.environ.get("APPDATA", "")),
                        ("Local", os.environ.get("LOCALAPPDATA", ""))):
        if not os.path.isdir(base):
            continue
        try:
            entries = list(os.scandir(base))
        except OSError:
            continue
        for entry in entries:
            if _is_link(entry.path):
                path = os.path.abspath(entry.path)
                key = _path_key(path)
                live_paths.add(key)
                record = records_by_path.get(key)
                actual_target = _link_target(path)
                if record:
                    real_path = os.path.abspath(record.get("real_path", actual_target))
                    target_exists = os.path.isdir(real_path)
                    target_matches = _path_key(actual_target) == _path_key(real_path)
                    status = "正常" if target_exists and target_matches else (
                        "目标不一致" if target_exists else "目标丢失"
                    )
                    results.append({**record, "link_path": path, "real_path": real_path,
                                    "from_history": False, "managed": True,
                                    "target_exists": target_exists, "status": status})
                else:
                    results.append({"name": entry.name, "link_path": path,
                                    "real_path": actual_target, "appdata_type": label,
                                    "from_history": False, "managed": False,
                                    "target_exists": os.path.isdir(actual_target),
                                    "status": "非本软件链接"})
    for record in history:
        if _path_key(record.get("link_path", "")) not in live_paths:
            results.append({**record, "from_history": True, "managed": True,
                            "target_exists": os.path.isdir(record.get("real_path", "")),
                            "status": "链接缺失"})
    return results
