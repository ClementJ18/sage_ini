"""PyQt6 desktop UI to browse SAGE objects: load data sources, search for an object,
and see its stats. The entry point; the UI is split across `browser.py` (main window),
`unit_panel.py` (stat view), `registry.py` (game-folder lookup) and `layout.py`.

Run from the repo root:
    .venv/Scripts/python sage_ui/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path

from sage_ui.browser import ICON_FILE, Browser  # noqa: E402
from sage_utils.widgets import run_app  # noqa: E402


def main() -> None:
    run_app(Browser, icon_file=ICON_FILE, anchor=__file__)


if __name__ == "__main__":
    main()
