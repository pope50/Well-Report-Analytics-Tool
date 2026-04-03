import streamlit.web.cli as stcli
import os, sys
import multiprocessing


def resolve_path(path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, path)


if __name__ == "__main__":
    # Required for Windows executables using multiprocessing
    multiprocessing.freeze_support()

    app_path = resolve_path("my_app.py")

    # Critical Flags for EXE:
    # 1. server.headless=true: Prevents it from trying to open a browser tab before the server starts
    # 2. global.developmentMode=false: Disables the "File Watcher" (which crashes EXEs)
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.headless=false",
        "--global.developmentMode=false",
    ]

    sys.exit(stcli.main())