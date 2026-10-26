# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/home/soluutions/Projects/LazyVA/run.py'],
    pathex=[],
    binaries=[('/home/soluutions/.local/share/uv/python/cpython-3.13.13-linux-x86_64-gnu/lib/libtcl9.0.so', '.'), ('/home/soluutions/.local/share/uv/python/cpython-3.13.13-linux-x86_64-gnu/lib/libtcl9tk9.0.so', '.')],
    datas=[('/home/soluutions/Projects/LazyVA/assets', 'assets'), ('/home/soluutions/Projects/LazyVA/.venv/lib/python3.13/site-packages/customtkinter', 'customtkinter')],
    hiddenimports=['PIL._tkinter_finder', 'pystray', 'pynput', 'pynput.keyboard', 'pynput.mouse', 'customtkinter', 'requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas', 'IPython', 'unittest', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LazyVA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/home/soluutions/Projects/LazyVA/assets/icon.ico'],
)
