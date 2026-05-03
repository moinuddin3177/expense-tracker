# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the Expense Tracker Streamlit app.
#
# Build:
#   pyinstaller expense_tracker.spec
#
# Output:  dist/ExpenseTracker/ExpenseTracker.exe  (Windows)
#          dist/ExpenseTracker/ExpenseTracker       (macOS/Linux)

from PyInstaller.utils.hooks import collect_all, collect_data_files

# ── Collect everything Streamlit needs (static assets, templates, etc.) ──────
st_datas, st_binaries, st_hidden = collect_all("streamlit")

# ── Other heavy packages that use lazy imports ────────────────────────────────
alt_datas, alt_binaries, alt_hidden = collect_all("altair")
pd_datas,  pd_binaries,  pd_hidden  = collect_all("pandas")
px_datas,  px_binaries,  px_hidden  = collect_all("plotly")
an_datas,  an_binaries,  an_hidden  = collect_all("anthropic")

all_datas = (
    st_datas + alt_datas + pd_datas + px_datas + an_datas
    # Bundle app.py and tracker.py into the frozen root so launcher.py can find them
    + [("app.py", "."), ("tracker.py", ".")]
)
all_binaries = st_binaries + alt_binaries + pd_binaries + px_binaries + an_binaries
all_hidden = (
    st_hidden + alt_hidden + pd_hidden + px_hidden + an_hidden
    + [
        "pydantic",
        "pydantic.v1",
        "email.mime.multipart",
        "email.mime.text",
    ]
)

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "PIL", "tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ExpenseTracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # no terminal window; errors go to a log file instead
    icon=None,       # replace with "icon.ico" / "icon.icns" if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ExpenseTracker",
)
