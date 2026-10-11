# -*- mode: python ; coding: utf-8 -*-
#
# Variante portable MONOFICHIER pour Windows.
# PyInstaller extrait les DLL sous son repertoire temporaire au demarrage,
# plutot que d'executer des DLL .NET portant le marquage web du ZIP telecharge.
# Aucune compression UPX ; conserve l'icone Windows.

a = Analysis(
    ['yt_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='All_Media_Download',
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
    icon=['logo.ico'],
)
