# PyInstaller: StatLab en modo «onedir» (arranca más rápido que onefile y deja las
# bibliotecas de Qt como archivos separados, como pide la LGPL).
#   uv run pyinstaller packaging/statlab.spec --noconfirm
import sys
import tomllib
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent  # noqa: F821 - SPECPATH lo define PyInstaller
PKG = ROOT / "packaging"
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

datas = []
datas += collect_data_files("statlab")  # tema (QSS, Inter, iconos) y datos de ejemplo
datas += collect_data_files("docx")  # plantilla por defecto de python-docx
datas += collect_data_files("reportlab")
datas += [(str(p), "licenses") for p in (PKG / "licenses").iterdir() if p.is_file()]

excludes = [
    "tkinter", "PyQt5", "PyQt6", "PySide2", "IPython", "jupyter", "notebook", "pytest", "pytestqt",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtQuick",
    "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtNetworkAuth", "PySide6.QtBluetooth",
    "matplotlib.backends.backend_qtagg", "matplotlib.backends.backend_tkagg",
]

a = Analysis(  # noqa: F821
    [str(PKG / "launch.py")],
    pathex=[str(ROOT / "src")],
    datas=datas,
    hiddenimports=[
        "statlab.modules.kmeans.module", "statlab.modules.kmeans.steps",
        "statlab.modules.kmeans.panels", "statlab.modules.kmeans.report",
        # matplotlib elige el backend por el formato al guardar: hay que incluirlos a mano
        "matplotlib.backends.backend_agg", "matplotlib.backends.backend_svg",
    ],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

icon = {"win32": PKG / "windows" / "statlab.ico", "darwin": PKG / "macos" / "statlab.icns"}.get(sys.platform)

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StatLab",
    console=False,  # app de ventana: sin consola negra en Windows
    icon=str(icon) if icon else None,
    upx=False,  # UPX dispara falsos positivos de antivirus
)
coll = COLLECT(exe, a.binaries, a.datas, name="StatLab", upx=False)  # noqa: F821

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="StatLab.app",
        icon=str(PKG / "macos" / "statlab.icns"),
        bundle_identifier="org.statlab.desktop",
        info_plist={
            "CFBundleDisplayName": "StatLab",
            "CFBundleShortVersionString": VERSION,
            "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.medical",
        },
    )
