# PyInstaller 打包指南

本指南说明如何把 Universal Manga Downloader 打包成 macOS `.app` 与 Windows 桌面应用，目标是让最终用户「下载即用」，无需安装 Python 或额外依赖。流程以 PyInstaller 为核心，涵盖准备工作、构建步骤、打包后的验证与维护建议。

> ⚠️ **跨平台说明**  
> PyInstaller 无法跨平台交叉编译，必须在目标操作系统上完成打包：macOS `.app` 需在 macOS 上构建，Windows `.exe`/安装包需在 Windows 上构建。

---

## 1. 前置条件

- macOS 12+ 或 Windows 10 64 位（管理员权限可选，用于后续签名／安装器生成）。  
- Python 3.10–3.12（建议与项目开发版本保持一致）。  
- 可写入仓库根目录，以生成 `build/`、`dist/` 等 PyInstaller 输出目录。  
- 对项目已有工作流的了解（参见 `ONBOARDING.md`、`DEVELOPMENT.md`）。

建议在各平台分别创建独立的虚拟环境，避免依赖污染。

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows（PowerShell）
python -m venv .venv
.venv\Scripts\Activate.ps1
```

创建虚拟环境后，安装项目依赖与 PyInstaller：

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

---

## 2. 目录与资源清单

PyInstaller 默认会把显式 import 的模块收集到可执行文件，但本项目存在 **动态加载的插件**（`plugins/*.py`），如果不额外处理会导致打包版本找不到插件。请确认以下资源：

| 资源 | 作用 | 打包策略 |
| --- | --- | --- |
| `manga_downloader.py` | Tkinter 入口脚本 | 作为 PyInstaller 主脚本 |
| `plugins/*.py` | 解析器、转换器插件（动态发现） | 以数据文件形式打入 |
| `config.py`、`core/`、`services/`、`utils/` | 常规模块 | PyInstaller 自动收集 |
| `requirements.txt` 中的三方库 | 运行时依赖 | 由 PyInstaller 自动收集；如出现缺失再添加隐藏导入 |

如需对 app 提供自定义图标，请准备：

- macOS：`assets/app.icns`
- Windows：`assets/app.ico`

并在 `spec` 中引用（见下文）。

---

## 3. 生成初始 `.spec` 文件

首次运行建议让 PyInstaller 自动生成基础配置，再手动调整。以下命令以图形化应用（无控制台窗口）为例：

```bash
pyinstaller \
  --name "UniversalMangaDownloader" \
  --windowed \
  --noconfirm \
  --noconsole \
  manga_downloader.py
```

命令完成后，仓库根目录会新增：

- `UniversalMangaDownloader.spec`：PyInstaller 配置文件
- `build/UniversalMangaDownloader/`：中间构建产物
- `dist/UniversalMangaDownloader/`：最终输出的可执行目录

接下来编辑生成的 `.spec` 文件，确保插件等资源被正确打包。

---

## 4. 自定义 `.spec` 文件

下面给出一个示例配置片段，重点在 `datas` 与 `hiddenimports`：

```python
# UniversalMangaDownloader.spec
from __future__ import annotations

import sys

block_cipher = None

a = Analysis(
    ["manga_downloader.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("plugins/*.py", "plugins"),
    ],
    hiddenimports=[
        "sv_ttk",
        "cloudscraper",
        "requests_toolbelt",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="UniversalMangaDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,  # macOS 若需拖放文件，可改成 True
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/app.icns" if sys.platform == "darwin" else "assets/app.ico",
)
```

调整要点：

1. **`datas`**：把整个 `plugins` 目录打入运行目录，保证 `PluginLoader` 能通过文件系统遍历。若后续增加其他动态资源（例如用户模板），可追加条目。格式：`("源文件模式", "目标子目录")`。在 Windows 上使用 `.spec` 可以避免命令行分隔符差异（`;` vs `:`）。
2. **`hiddenimports`**：列出运行时通过字符串导入的模块，避免漏打包。当前示例包含 `sv_ttk`、`cloudscraper`、`requests_toolbelt`；根据实际 mypy/运行结果再补充。
3. **`icon`**：根据平台使用不同图标（可选）。
4. **`argv_emulation`**：macOS 若希望支持把文件拖到应用图标上，可以改为 `True`（会轻微增加启动时间）。

保存 `.spec` 文件后，清理旧的 `build/`、`dist/` 再重新构建：

```bash
pyinstaller UniversalMangaDownloader.spec --clean
```

---

## 5. 平台特定说明

### 5.1 macOS

1. 构建输出：`dist/UniversalMangaDownloader.app`。可直接双击运行；若来自未签名开发者，首次启动需要在「系统设置 → 隐私与安全性」中允许。  
2. 可选：使用 `codesign` 对 `.app` 进行开发者签名，后续可送 notarization。示例命令：

   ```bash
   codesign --deep --force --sign "Developer ID Application: Your Name (TEAMID)" dist/UniversalMangaDownloader.app
   ```

3. 若要打包成 `.dmg`，推荐使用 `create-dmg` 或者 Xcode 命令行工具。

### 5.2 Windows

1. 构建输出：`dist/UniversalMangaDownloader/UniversalMangaDownloader.exe` 与依赖文件夹。  
2. 如需单文件模式可在 `.spec` 中把 `EXE` 包裹进 `COLLECT` 或使用 `--onefile`，但启动时 PyInstaller 会先解压到临时目录，GUI 应用体积较大会略慢。  
3. 建议使用 Inno Setup 或 MSIX 打包成安装向导，顺便配置桌面/开始菜单快捷方式以及卸载信息。  
4. 若要签名，使用 `signtool.exe`：

   ```powershell
   signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com dist\UniversalMangaDownloader\UniversalMangaDownloader.exe
   ```

---

## 6. 构建后验证清单

1. **基本运行**：在目标系统双击打开，确认 Tkinter GUI 正常显示、主题加载成功。  
2. **插件自检**：检查设置页面的插件列表，确保所有内置解析器/转换器都在。若缺失，请确认 `plugins/*.py` 是否正确打包。  
3. **网络功能**：执行一次示例下载，观察日志窗口是否出现网络错误或缺失依赖。  
4. **文件输出**：验证 CBZ/PDF 等转换结果写入正常路径。  
5. **防病毒/安全警报**：在 Windows 上尤其需要测试，未签名可执行文件可能被拦截。  
6. **回归测试**：至少运行 `ruff check .` 与 `mypy .`，保证源码在打包前处于健康状态。

---

## 7. 常见问题排查

| 现象 | 可能原因 | 处理建议 |
| --- | --- | --- |
| 启动后插件列表为空 | `plugins` 未被复制到运行目录 | 检查 `.spec` 的 `datas` 配置，确认构建输出内存在 `plugins/*.py` |
| 运行时报 `ModuleNotFoundError` | 隐藏导入缺失 | 把报错模块加入 `.spec` 的 `hiddenimports` |
| Windows 启动时弹出控制台 | 未使用 `--windowed` / `.spec` 中 `console=True` | 把命令行参数改为 `--windowed` 或在 `.spec` 中设 `console=False` |
| macOS 提示「已损坏或无法打开」 | 未签名或 Gatekeeper 拦截 | 使用 `codesign` 签名，或让用户通过右键→打开绕过 |
| 打包体积过大 | 带入了调试符号或冗余库 | 评估 `excludes`、关闭 `--debug`，必要时使用 UPX 压缩（需额外安装） |

---

## 8. 维护建议

- 将 `pyinstaller` 与 `.spec` 构建步骤纳入 CI，确保每次改动都能产出可运行的包。  
- 在版本发布前，分别在 macOS 与 Windows 上执行「打包 → 验证清单」，并记录构建命令、签名证书信息。  
- 每次新增插件或资源时，同步更新 `.spec` 的 `datas`/`hiddenimports` 并附上说明。  
- 若未来引入自动更新或安装器，请在此文档追加相应流程，保持唯一可信来源。

---

完成以上步骤后，即可为两大桌面平台提供“即装即用”的 PyInstaller 版本。如流程中遇到新的问题或需要额外资源，请在仓库中记录，以便团队协作与后续维护。***
