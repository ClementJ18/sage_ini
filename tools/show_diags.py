"""Print diagnostics with context for one file. Usage: show_diags.py <file> [max]"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sage_ini.parser.blockparser import parse_file  # noqa: E402,PLC0415
from sage_ini.parser.io import read_text  # noqa: E402,PLC0415


def main() -> int:
    path = Path(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    result = parse_file(path)
    lines = read_text(path).splitlines()

    print(f"{len(result.diagnostics)} diagnostics")
    for diag in list(result.diagnostics)[:limit]:
        print(diag)
        start = max(0, diag.span.line_start - 7)
        stop = min(len(lines), diag.span.line_start + 2)
        for number in range(start, stop):
            marker = ">>" if number == diag.span.line_start - 1 else "  "
            print(f"  {marker} {number + 1:5} {lines[number]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
