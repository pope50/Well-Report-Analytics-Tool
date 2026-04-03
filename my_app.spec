# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata

# 1. Define your main scripts
datas = [
    ('my_app.py', '.'), 
    ('my_pipeline.py', '.'),
]

# Add Streamlit's internal metadata (Crucial for the web server to boot)
datas += copy_metadata('streamlit')

binaries = []
hiddenimports = [
    'tkinter', 
    'tkinter.filedialog', 
    'pandas', 
    'streamlit',
    'pdfplumber',
    'altair',        
    'pyarrow',       
    'streamlit.runtime.scriptrunner.magic_funcs',
    'openpyxl',
    're'
]

# 2. Automatically collect all metadata and sub-modules
for module_name in ['streamlit', 'pandas', 'pdfplumber']:
    tmp_ret = collect_all(module_name)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

block_cipher = None

a = Analysis(
    ['my_run_app.py'], 
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,    # Bundles binaries into the exe
    a.zipfiles,    # Bundles zipfiles into the exe
    a.datas,       # Bundles your data/scripts into the exe
    [],
    name='Well_Report_Analytics',
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
    icon='logo.ico'
)

