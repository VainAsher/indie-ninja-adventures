# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

a = Analysis(
    ['..\\demo_game.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../assets', 'assets'),
        ('../config', 'config'),
        ('../data', 'data'),
    ],
    hiddenimports=[
        # Core dependencies
        'pygame',
        'pygame.mixer',
        'pygame.font',
        'pygame.transform',
        'pygame.time',
        'pygame.draw',
        'pygame.surface',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        # Game modules
        'config',
        'config.build_config',
        'config.settings',
        'config.physics_constants',
        'core',
        'systems',
        'rendering',
        'network',
        'entities',
        'game',
        'ui',
        'mechanics',
        'data',
        'utils',
        'dev_tools',
        'dev_tools.dev_console',
        'dev_tools.hot_reload',
        # Ensure all submodules are included
        'entities.player',
        'entities.enemy',
        'entities.npc',
        'entities.companions',
        'rendering.tile_loader',
        'rendering.npc_prompt',
        'ui.inventory_ui',
        'ui.dialogue_ui',
        'game.dialogue_system',
        'game.story_manager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
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
    [],
    exclude_binaries=True,
    name='ninja_dash_dev',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # CONSOLE VISIBLE for development
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/icon.ico' if os.path.exists('../assets/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ninja_dash_dev',
)
