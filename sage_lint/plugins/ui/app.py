"""PyQt6 desktop window over `sage_lint lint`, for teammates who would rather not use the
command line. Point it at a mod folder, set a few options, press Check, and browse the
errors and warnings in a searchable, sortable table. The window lives in `window.py`; the
lint runs the CLI in-process (see `runner.py`).

Run from the repo root:
    .venv/Scripts/python sage_lint/plugins/ui/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root on path

from sage_lint.plugins.ui.window import APP_NAME, ICON_FILE, LintWindow  # noqa: E402
from sage_utils.widgets import run_app  # noqa: E402


def main() -> None:
    run_app(LintWindow, icon_file=ICON_FILE, anchor=__file__, app_name=APP_NAME)


if __name__ == "__main__":
    main()
