# -*- mode: python ; coding: utf-8 -*-
# Build the SAGE Lint window into a single standalone .exe a teammate can run without Python:
#   pyinstaller sage-lint-ui.spec
# The result is dist/SAGE Lint.exe. The model registry is populated by ordinary imports from
# sage_lint.cli, so PyInstaller's static analysis finds it — no hiddenimports needed.


a = Analysis(
    ['sage_lint\\plugins\\ui\\app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('sage_lint/plugins/ui/icon.ico', '.'),  # window/taskbar icon, found via sys._MEIPASS
    ],
    hiddenimports=['tomllib'],  # .sagelint is TOML; ensure the stdlib parser is bundled
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
    name='SAGE Lint',
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
    icon=['sage_lint\\plugins\\ui\\icon.ico'],
)
