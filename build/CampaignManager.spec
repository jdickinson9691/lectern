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
    hiddenimports=['app.main', 'openpyxl', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='Lectern', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=False,
    icon=str(ROOT / 'app' / 'resources' / 'lectern_icon.png'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name='Lectern')
