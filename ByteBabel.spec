# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('/Users/hoangvu/Desktop/github.com/transcript-app/helpers/system_audio_capture', 'helpers/'), ('/Users/hoangvu/Desktop/github.com/transcript-app/assets/icon.png', 'assets/')]
binaries = []
hiddenimports = ['customtkinter', 'soniox', 'sounddevice', '_sounddevice_data', 'websockets', 'keyring.backends', 'PIL', 'numpy']
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('soniox')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['/Users/hoangvu/Desktop/github.com/transcript-app/src/bytebabel/main.py'],
    pathex=['/Users/hoangvu/Desktop/github.com/transcript-app/src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='ByteBabel',
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
    icon=['/Users/hoangvu/Desktop/github.com/transcript-app/assets/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ByteBabel',
)
app = BUNDLE(
    coll,
    name='ByteBabel.app',
    icon='/Users/hoangvu/Desktop/github.com/transcript-app/assets/icon.icns',
    bundle_identifier=None,
)
