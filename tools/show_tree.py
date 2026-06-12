"""Print the top-level (and optionally nested) block spans of a parsed file.

Usage: show_tree.py <file> [depth]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sage_ini.parser.ast import Block, ScriptBlock  # noqa: E402,PLC0415
from sage_ini.parser.blockparser import parse_file  # noqa: E402,PLC0415


def dump(nodes, depth, max_depth):
    for node in nodes:
        if isinstance(node, Block):
            label = f" {node.label}" if node.label else ""
            span = f"[{node.span.line_start}-{node.span.line_end}]"
            print(f"{'  ' * depth}{node.name}{label}  {span}")
            if depth + 1 < max_depth:
                dump(node.children, depth + 1, max_depth)
        elif isinstance(node, ScriptBlock):
            print(f"{'  ' * depth}<script>  [{node.span.line_start}-{node.span.line_end}]")


def main() -> int:
    path = Path(sys.argv[1])
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    result = parse_file(path)
    dump(result.document.children, 0, max_depth)
    for diag in result.diagnostics:
        print(diag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
