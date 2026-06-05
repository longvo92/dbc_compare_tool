# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


block_cipher = None
PROJECT_ROOT = Path(SPECPATH).parent
RESOURCE_DIR = PROJECT_ROOT / "resources"

a = Analysis(
    [str(PROJECT_ROOT / "src" / "dbc_compare_tool" / "__main__.py")],
    pathex=[str(PROJECT_ROOT), str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=[
        (str(RESOURCE_DIR / "vinfast_logo.png"), "resources"),
        (str(RESOURCE_DIR / "help" / "user_guide.md"), "resources/help"),
        (str(RESOURCE_DIR / "help" / "release_notes.md"), "resources/help"),
        (str(RESOURCE_DIR / "help" / "about.md"), "resources/help"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DBCCompareTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(RESOURCE_DIR / "VinFast_logo.ico"),
    version=str(RESOURCE_DIR / "version_info.txt"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DBCCompareTool",
)
