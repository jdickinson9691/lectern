# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(ROOT / 'run.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'app' / 'resources'), 'app/resources'),
        (str(ROOT / 'seeds'), 'seeds'),
        (str(ROOT / 'docs'), 'docs'),
    ],
    hiddenimports=['app.main', 'openpyxl', 'pypdf', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
# Qt6Core uses the Windows ICU API. A third-party icuuc.dll on PATH (for
# example Poppler's versioned ICU build) has incompatible exports and causes
# QtCore to fail at startup when PyInstaller collects it into _internal.
a.binaries = TOC([entry for entry in a.binaries if Path(entry[0]).name.lower() not in {'icuuc.dll', 'icudt78.dll'}])
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='Lectern', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=False,
    icon=str(ROOT / 'app' / 'resources' / 'lectern_icon.png'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name='Lectern')
