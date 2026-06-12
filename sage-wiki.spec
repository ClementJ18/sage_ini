# -*- mode: python ; coding: utf-8 -*-
# Build the Edain Wiki Assistant into a single windowed exe:
#     pyinstaller sage-wiki.spec
# The result is dist/Edain Wiki Assistant.exe.


a = Analysis(
    ['sage_wiki\\app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('sage_wiki/icon.ico', '.'),  # bundled beside the code, found via sys._MEIPASS
        ('sage_utils/assets/background.png', 'assets'),  # parchment behind portraits
    ],
    # keyring loads its backend dynamically via entry points; name the Windows
    # Credential Manager backend (and its win32ctypes dependency) explicitly so the
    # frozen exe can still store the remembered password.
    hiddenimports=[
        'mwclient',
        'mwparserfromhell',
        'keyring.backends.Windows',
        'win32ctypes.core',
    ],
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
    name='Edain Wiki Assistant',
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
    icon=['sage_wiki\\icon.ico'],
)
