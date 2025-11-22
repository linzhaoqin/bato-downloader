# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ["manga_downloader.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("plugins/*.py", "plugins"),
        ("assets/*.png", "assets"),  # Include assets if needed by code, though guide mentioned .icns/.ico specifically for app icon
    ],
    hiddenimports=[
        "sv_ttk",
        "cloudscraper",
        # "requests_toolbelt", # Not in requirements.txt, checking if needed. Guide had it.
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/app.icns" if sys.platform == "darwin" else "assets/app.ico", # Commented out as assets are missing
)

# For macOS .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='UniversalMangaDownloader.app',
        icon=None, # "assets/app.icns",
        bundle_identifier='com.linzhaoqin.manga-downloader',
    )
