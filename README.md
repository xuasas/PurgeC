<p align="center">
  <img src="https://img.shields.io/badge/version-1.0-blue?style=flat-square" alt="version">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2B-lightgrey?style=flat-square" alt="platform">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="license">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="python">
</p>

<h1 align="center">🧹 PurgeC</h1>

<p align="center"><strong>C 盘空间整理工具 · 本地运行 · 操作可追溯</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/🛡️_所有删除进回收站-安全可恢复-4caf50?style=for-the-badge" alt="safe">
  <img src="https://img.shields.io/badge/📋_全部操作有日志-可追溯-2196f3?style=for-the-badge" alt="logged">
  <img src="https://img.shields.io/badge/🔗_NTFS_Junction_迁移-零占用-ff9800?style=for-the-badge" alt="junction">
</p>

---

## 📖 目录

- [这是什么？](#-这是什么)
- [✨ 核心功能](#-核心功能)
  - [🔍 残留扫描](#-残留扫描)
  - [📊 空间分析](#-空间分析)
  - [🗑️ 临时文件清理](#️-临时文件清理)
  - [📦 应用数据迁移](#-应用数据迁移)
- [🛡️ 安全设计](#️-安全设计)
- [📸 界面预览](#-界面预览)
- [🚀 快速开始](#-快速开始)
  - [直接下载（推荐）](#直接下载推荐)
  - [从源码运行](#从源码运行)
  - [自行打包](#自行打包)
- [🏗️ 项目结构](#️-项目结构)
- [🔧 技术栈](#-技术栈)
- [❓ 常见问题](#-常见问题)
- [🤝 贡献](#-贡献)
- [📄 许可证](#-许可证)

---

## 🤔 这是什么？

**PurgeC** 是一款 Windows 桌面工具，专门帮助你回收 C 盘空间。它不会"一键清理"——而是**扫描 → 展示 → 由你审阅 → 确认后再操作**。所有删除都进入回收站（而非永久删除），所有操作都有日志可查。

> 💡 PurgeC **完全开源、免费**。如果你是通过付费购买获得它的，很可能被忽悠了——请谨慎核实出售方。

---

## ✨ 核心功能

PurgeC 提供四个功能标签页，覆盖不同的空间回收场景：

### 🔍 残留扫描

自动检测卸载软件后遗留在 `AppData` 以及系统临时/诊断目录中的文件和文件夹。

| 扫描范围 | 说明 |
|---------|------|
| `%LOCALAPPDATA%` | 当前用户的 Local 应用数据 |
| `%APPDATA%` | 当前用户的 Roaming 应用数据 |
| 系统临时 / 诊断 | `Windows\Temp`、`Minidump`、`LiveKernelReports`、WER 错误报告 |
| 自选目录 | 任意自定义路径 |

**智能分类**：每条结果会通过注册表交叉比对已安装程序，标注风险等级：

| 风险 | 颜色标识 | 说明 |
|------|---------|------|
| 🟢 低 | 绿色 | 明确的缓存、临时文件、崩溃诊断文件（如 `cache`、`.tmp`、`.dmp`） |
| 🟡 中 | 黄色 | 程序名称完全匹配，且原安装目录不存在 → 疑似卸载残留 |
| 🔴 高 | 红色 | 程序名称完全匹配，软件可能仍在使用 → 删除会丢失配置/数据 |

### 📊 空间分析

以**树形目录 + 横向柱状图**直观展示磁盘空间占用。

- 递归文件夹大小统计（可调节深度 1–5 级）
- 双击展开子目录
- **Top 10 柱状图**：一眼看清谁占的空间最多
- 支持选择任意磁盘/目录作为扫描起点
- 自动跳过系统关键目录（`Windows`、`Program Files`、`ProgramData` 等）

### 🗑️ 临时文件清理

一键扫描三大临时目录：

- `%TEMP%`
- `%TMP%`
- `C:\Windows\Temp`

所有结果按大小降序排列，**默认全选**（因为本身就是临时文件），支持批量移至回收站。

### 📦 应用数据迁移

这是 PurgeC 的**杀手级功能**——将 AppData 中体积较大的文件夹迁移到其他磁盘，并在原位创建 **NTFS Junction（目录链接）**，对应用程序完全透明。

```
迁移前                          迁移后
C:\Users\...\AppData\           C:\Users\...\AppData\
  └── Adobe\          ──→         └── Adobe\  (Junction)
      └── ...                          │
                                       └── D:\PurgeC-Migrated\Local\Adobe\  (真实数据)
```

**特性**：

- 仅允许跨分区迁移（同盘迁移没有意义）
- 迁移前检查目标磁盘剩余空间
- 迁移失败**自动回滚**
- 持久化迁移历史到 `%LOCALAPPDATA%\PurgeC\migrate_history.json`（原子写入，不怕断电）
- 支持**一键还原**：删除 Junction 并将数据移回原位
- 仅还原由 PurgeC 创建的链接（校验记录，拒绝操作未知链接）
- 列出所有现有 Junction 及其状态：✅ 正常 / ⚠️ 目标丢失 / ⚠️ 链接缺失

---

## 🛡️ 安全设计

PurgeC 从架构层面遵循"宁可不够激进，也不误删数据"的原则。

| 层面 | 措施 |
|------|------|
| **删除方式** | 使用 [`send2trash`](https://github.com/arsenetar/send2trash) 将文件移入 Windows 回收站，**所有删除均可从回收站还原** |
| **操作日志** | 每次删除操作写入 `purgec.log`，记录时间、路径和结果 |
| **迁移验证** | 迁移前校验：不同分区 ✓ 空闲空间充足 ✓ 目标不存在 ✓ 源路径非链接 ✓ |
| **迁移回滚** | 若迁移中途失败，自动将数据移回原位；若回滚也失败，数据安全保留在目标位置 |
| **还原保护** | 还原 Junction 时校验迁移记录，仅还原 PurgeC 创建的链接 |
| **原子写入** | 迁移历史写入 `.tmp` → `os.replace()`，避免写一半断电导致 JSON 损坏 |
| **不跟随链接** | 扫描时 `follow_symlinks=False`，防止循环引用导致死循环或重复计算 |
| **用户审阅** | 高风险项**不预勾选**，必须手动确认后才清理 |

---

## 📸 界面预览

> 如需添加截图，请将图片放入仓库的 `screenshots/` 目录，然后取消下方注释并填入路径。

<!--
### 残留扫描
![残留扫描](screenshots/scan.png)

### 空间分析
![空间分析](screenshots/space.png)

### 临时文件
![临时文件](screenshots/temp.png)

### 应用数据迁移
![应用数据迁移](screenshots/migrate.png)
-->

---

## 🚀 快速开始

### 直接下载（推荐）

前往 [Releases](https://github.com/Github-Xuasas/PurgeC/releases) 页面下载最新版 `PurgeC_Setup.exe` 安装程序。

- 双击安装，按向导完成
- 安装程序会自动创建桌面快捷方式
- 首次运行建议**以管理员身份运行**（软件内有"管理员重启"按钮）

> 📌 要求：Windows 10 1809+ / Windows 11，64 位

### 从源码运行

```powershell
# 1. 克隆仓库
git clone https://github.com/Github-Xuasas/PurgeC.git
cd PurgeC

# 2. 创建虚拟环境（推荐）
py -3 -m venv .venv
.venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行
python main.py
```

### 自行打包

#### PyInstaller 打包

```powershell
pip install pyinstaller

# 单文件模式（启动略慢，分发方便）
pyinstaller --noconfirm --clean --onefile --windowed --name PurgeC --collect-all sv_ttk main.py

# 目录模式（启动更快）
pyinstaller --noconfirm --clean --onedir --windowed --name PurgeC --collect-all sv_ttk main.py
```

输出位于 `dist\` 目录。

#### Inno Setup 安装程序

仓库提供了 `setup.iss`，使用 [Inno Setup 6](https://jrsoftware.org/isinfo.php) 打开并编译即可生成 `PurgeC_Setup.exe`。

> ⚠️ 建议**不要使用 UPX 压缩**，可能导致杀毒软件误报。

---

## 🏗️ 项目结构

```
PurgeC/
├── main.py                  # 入口：DPI 感知、管理员检测/UAC 提权、启动 GUI
├── scanner.py               # 扫描引擎：注册表读取、AppData 残留检测、文件夹大小统计
├── migrate.py               # 安全迁移：移动 AppData + 创建 NTFS Junction、还原支持
├── cleaner.py               # 安全清理：send2trash 封装 + 操作日志
├── gui/
│   ├── __init__.py          # 包标记
│   ├── app.py               # 主窗口：4 标签页、主题切换、状态栏
│   ├── scan_tab.py          # "残留扫描" 标签页
│   ├── space_tab.py         # "空间分析" 标签页（树形图 + 柱状图）
│   ├── temp_tab.py          # "临时文件" 标签页
│   ├── migrate_tab.py       # "应用数据迁移" 标签页
│   └── widgets.py           # 共享组件：format_size()、ProgressDialog、CheckableTreeview
├── requirements.txt         # 运行时依赖
├── PurgeC.spec              # PyInstaller 打包配置
├── setup.iss                # Inno Setup 安装脚本
└── 打包教程.md              # 中文打包教程
```

### 架构简图

```
┌─────────────────────────────────────────────┐
│                    main.py                   │
│  DPI 感知 → 管理员检测 → UAC 提权 → 启动    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│                 gui/app.py                   │
│  Tk 主窗口 · sv_ttk 主题 · 4 标签页         │
├──────────┬──────────┬──────────┬────────────┤
│ ScanTab  │ SpaceTab │ TempTab  │ MigrateTab │
└────┬─────┴────┬─────┴────┬─────┴──────┬─────┘
     │          │          │            │
┌────▼────┐ ┌───▼────┐ ┌──▼────┐ ┌────▼──────┐
│scanner  │ │scanner │ │scanner│ │ migrate   │
│  .py    │ │  .py   │ │  .py  │ │   .py     │
└────┬────┘ └────────┘ └──┬────┘ └─────┬─────┘
     │                    │            │
┌────▼────────────────────▼────────────▼──────┐
│               cleaner.py                     │
│        send2trash · 操作日志                 │
└──────────────────────────────────────────────┘
```

---

## 🔧 技术栈

| 类别 | 技术 |
|------|------|
| **语言** | Python 3.11 |
| **GUI 框架** | Tkinter + [Sun Valley ttk](https://github.com/rdbende/Sun-Valley-ttk-theme)（深色/浅色主题） |
| **字体** | Microsoft YaHei UI |
| **并发** | `threading.Thread`（守护线程扫描，GUI 不卡顿） |
| **注册表** | `winreg`（读取已安装程序列表） |
| **目录链接** | `mklink /J`（NTFS Junction，无需开发者模式） |
| **回收站** | [`send2trash`](https://github.com/arsenetar/send2trash) |
| **打包** | PyInstaller + Inno Setup 6 |

---

## ❓ 常见问题

<details>
<summary><strong>Q: PurgeC 会删除我的个人文件吗？</strong></summary>

不会。PurgeC **只删除你手动勾选并确认的项目**，而且所有删除都进入回收站，不是永久删除。高风险项目默认不勾选。
</details>

<details>
<summary><strong>Q: 迁移 AppData 文件夹后，软件还能正常运行吗？</strong></summary>

能。PurgeC 在迁移后会在原位创建 **NTFS Junction（目录链接）**，对应用程序完全透明，软件感知不到数据已经移走。
</details>

<details>
<summary><strong>Q: 迁移失败了怎么办？数据会丢吗？</strong></summary>

不会。迁移操作有完整的失败回滚机制：如果移动过程中出错，PurgeC 会自动把数据移回原位。即使回滚也失败，数据也安全保留在目标位置。
</details>

<details>
<summary><strong>Q: 为什么需要管理员权限？</strong></summary>

部分清理操作（如 `Windows\Temp`、系统诊断文件）和创建 Junction 需要管理员权限。软件在普通权限下也可以运行，但功能会受限——你可以随时点击"管理员重启"按钮提升权限。
</details>

<details>
<summary><strong>Q: 迁移和还原需要多长时间？</strong></summary>

取决于文件夹大小和磁盘速度。迁移本质上是**移动文件**（同盘移动是秒级的，跨盘移动取决于数据量和磁盘读写速度），而不是复制+删除——所以通常很快。
</details>

<details>
<summary><strong>Q: 支持哪些 Windows 版本？</strong></summary>

Windows 10 1809+ 和 Windows 11，64 位。不支持 32 位系统，不支持 Windows 7 / 8 / 8.1（未测试，理论上可能运行但不受支持）。
</details>

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

- 🐛 发现 Bug？请提交 Issue 并附上 `purgec.log` 和相关截图
- 💡 有新功能建议？请先开 Issue 讨论
- 🔧 想贡献代码？Fork → 修改 → PR，任何改进都欢迎

---

## 📄 许可证

本项目采用 **MIT License** 开源。详见 [LICENSE](LICENSE) 文件。

> ⚠️ **注意**：PurgeC 完全免费。如果你通过付费渠道获得它，请立即要求退款并向平台举报——你被骗了。

---

<p align="center">
  <sub>Made with ❤️ by <a href="https://github.com/Github-Xuasas">Github-Xuasas</a></sub>
</p>
