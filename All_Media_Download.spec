# -*- mode: python ; coding: utf-8 -*-
#
# Distribution Windows en dossier (onedir) :
# - pas d'extraction complete dans %TEMP% a chaque demarrage
# - pas de compression UPX, parfois signalee par les antivirus
# - dependencies PyInstaller conservees dans le sous-dossier _internal
# Le logo est integre a l'executable ; les copies .ico et .jpg
# sont ajoutees a cote de l'executable par GitHub Actions.

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
