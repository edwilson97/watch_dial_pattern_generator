# Build with: python -m PyInstaller --clean --noconfirm WatchDialPatternGenerator.spec
import sys
from PyInstaller.utils.hooks import collect_all

# PyVista and VTK load modules dynamically. Include their modules, native
# libraries, and data rather than relying solely on static import analysis.
datas, binaries, hiddenimports = [], [], []
for package in ('pyvista', 'vtkmodules'):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

a = Analysis(
    ['frozen_entry.py'],
    pathex=[],
    binaries=binaries,
    datas=datas + [('LICENSE', '.'), ('README.md', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='WatchDialPatternGenerator',
    console=False,
    upx=False,
)
collection = COLLECT(
    exe, a.binaries, a.datas,
    name='WatchDialPatternGenerator',
    upx=False,
)
if sys.platform == 'darwin':
    app = BUNDLE(
        collection,
        name='WatchDialPatternGenerator.app',
        bundle_identifier='com.bridgewatches.watchdialpatterngenerator',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
        },
    )
