# -*- mode: python ; coding: utf-8 -*-
# DIAGNOSTIC EXPERIMENTAL : EXE Windows avec runtime persistant.
# Contrairement au monofichier, aucun DLL n'est extrait dans %TEMP%
# au lancement. Les dependencies restent dans Runtime/.
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
    [],
    exclude_binaries=True,
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
    contents_directory='Runtime',
    icon=['logo.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='All_Media_Download',
)
