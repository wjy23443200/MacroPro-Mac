# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['macro_pro.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pynput.keyboard._darwin', 'pynput.mouse._darwin'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='宏工具独立版',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='宏工具独立版',
)
app = BUNDLE(
    coll,
    name='宏工具独立版.app',
    icon=None,
    bundle_identifier='local.macro.standalone',
    info_plist={'CFBundleShortVersionString': '1.1', 'CFBundleVersion': '2', 'LSMinimumSystemVersion': '15.0', 'NSInputMonitoringUsageDescription': '用于录制鼠标点击和识别全局快捷键。'},
)
