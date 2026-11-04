# -*- mode: python ; coding: utf-8 -*-
#
# Variante portable MONOFICHIER pour Windows.
# PyInstaller extrait les DLL sous son repertoire temporaire au demarrage,
# plutot que d'executer des DLL .NET portant le marquage web du ZIP telecharge.
# Aucune compression UPX ; conserve l'icone Windows.

# Inclure le moteur Twitch alternatif et ses plugins dans l'EXE autonome.
# Le chargement des plugins Streamlink est dynamique : leurs ressources et
# imports doivent être collectés explicitement par PyInstaller.
from PyInstaller.utils.hooks import collect_all

streamlink_datas, streamlink_binaries, streamlink_hiddenimports = collect_all('streamlink')

a = Analysis(
    ['yt_app.py'],
    pathex=[],
    binaries=streamlink_binaries,
    datas=streamlink_datas,
    hiddenimports=streamlink_hiddenimports,
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
