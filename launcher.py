"""
PyInstaller entry point.

When frozen, this file is the executable. It boots Streamlit's internal CLI
so that PyInstaller can trace all imports at build time, then opens a browser
tab automatically before the server starts.
"""

import sys
import threading
import time
import webbrowser
from pathlib import Path


def _app_path() -> str:
    """Return the absolute path to app.py whether running frozen or from source."""
    if getattr(sys, "frozen", False):
        return str(Path(sys._MEIPASS) / "app.py")
    return str(Path(__file__).parent / "app.py")


def _open_browser() -> None:
    time.sleep(3)  # give the server a moment to bind
    webbrowser.open("http://localhost:8501")


def main() -> None:
    threading.Thread(target=_open_browser, daemon=True).start()

    sys.argv = [
        "streamlit",
        "run",
        _app_path(),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.port=8501",
    ]

    from streamlit.web import cli as stcli
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
