"""Diagnostics for a root file with includes expanded across layers.

Usage: show_diags_expanded.py <file> <layer> [<layer> ...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sage_ini.parser.blockparser import parse_file  # noqa: E402,PLC0415

path = Path(sys.argv[1])
layers = [Path(p) for p in sys.argv[2:]]
result = parse_file(path, resolve_includes=True, include_layers=layers)
print(f"{len(result.diagnostics)} diagnostics")
for diag in result.diagnostics:
    print(diag)
