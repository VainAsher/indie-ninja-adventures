# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the standalone launcher exe.
# Builds as a single onefile exe with no console window.

import os
import sys

block_cipher = None

a = Analysis(
    ['..\\launcher\\launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle version.json so the launcher can read the installed version
        ('../version.json', '.'),
        # Bundle splash image for the launcher UI background
        ('../assets/splash/landing.png', 'assets/splash'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        '_tkinter',
        'urllib.request',
        'urllib.error',
        'hashlib',
        'threading',
        'subprocess',
        'json',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pygame',
        'PIL',
        'pytest',
        'numpy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ninja_dash_launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/icon.ico' if os.path.exists('../assets/icon.ico') else None,
)
