# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = [('app/assets', 'app/assets'), ('assets', 'assets')]
binaries = []
hiddenimports = [
    'keyboard',
    'pyperclip',
    'winreg',
    'ctypes',
    'app',
    'app.core',
    'app.core.assets',
    'app.core.clipboard',
    'app.core.config',
    'app.core.engine_manager',
    'app.core.shortcuts',
    'app.core.theme',
    'app.engines',
    'app.engines.gemini_engine',
    'app.ui',
    'app.ui.about_dialog',
    'app.ui.api_guide_dialog',
    'app.ui.diff_window',
    'app.ui.settings_dialog',
    'app.utils',
    'app.utils.autostart',
    'app.utils.diff_highlighter',
    'app.utils.foreign_words',
    'app.utils.i18n',
    'app.utils.punctuation_formatter',
    'app.utils.bijoy_converter',
    'app.utils.offline_checker',
    'app.utils.bd_gazetteer',
    'app.engines.offline_checker',
]

# Collect all resources and schemas for google-genai
try:
    tmp_ret = collect_all('google.genai')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"collect_all(google.genai) warning: {e}")

a = Analysis(
    ['app/main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtPdf',
        'PySide6.QtPdfWidgets',
        'PySide6.QtQml',
        'PySide6.QtQuick',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BanglaProofreader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/logo.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BanglaProofreader',
)
