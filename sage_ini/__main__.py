"""Command-line entry point: `python -m sage_ini <command>` (or `sage-ini`).

- `stats <dir>`  — the corpus parse-rate scoreboard.
- `lint <paths>` — assemble files/folders and report parse/load/conversion problems
  (the "does it convert?" facts; judgment rules live in `sage_lint`).
- `xref <dir> <name>` — what a definition references and what references it.
"""

import argparse
from pathlib import Path

from sage_ini.loader import load_game
from sage_ini.model.game import Game
from sage_ini.model.xref import Xref
from sage_ini.parser.blockparser import parse_file
from sage_ini.parser.diagnostics import Diagnostics, Severity
from sage_ini.parser.location import Span
from sage_ini.stats import compute_scoreboard, format_scoreboard


def _lint_paths(paths: list[Path]) -> Diagnostics:
    """Parse + load + validate each path (a folder is assembled as a whole game)."""
    diagnostics = Diagnostics()
    for path in paths:
        if path.is_dir():
            loaded = load_game(path)
            diagnostics.items.extend(loaded.diagnostics.items)
            diagnostics.items.extend(loaded.game.validate().items)
            continue
        result = parse_file(path, resolve_includes=True)
        diagnostics.items.extend(result.diagnostics.items)
        game = Game()
        try:
            game.load_document(result.document)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            diagnostics.add("load-error", f"{exc}", Span(str(path), 1, 1))
        diagnostics.items.extend(game.validate().items)
    return diagnostics


def _run_lint(paths: list[Path]) -> int:
    diagnostics = list(_lint_paths(paths))
    diagnostics.sort(key=lambda d: (d.span.file, d.span.line_start))
    for diagnostic in diagnostics:
        print(diagnostic)
    errors = sum(1 for d in diagnostics if d.severity is Severity.ERROR)
    print(f"{errors} error(s), {len(diagnostics) - errors} other(s)")
    return 1 if errors else 0


def _run_xref(root: Path, name: str) -> int:
    xref = Xref(load_game(root).game)
    matches = [
        (key, obj)
        for key, table in xref.game.tables.items()
        for obj_name, obj in table.items()
        if obj_name == name
    ]
    if not matches:
        print(f"no definition named {name!r} under {root}")
        return 1
    for key, obj in matches:
        print(f"{name} [{key}]")
        print("  references:")
        for target in sorted(xref.references(obj), key=lambda o: (o.key or "", o.name)):
            print(f"    -> {target.name} [{target.key}]")
        print("  referenced by:")
        for source in sorted(xref.referenced_by(obj), key=lambda o: (o.key or "", o.name)):
            print(f"    <- {source.name} [{source.key}]")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sage_ini")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stats = subparsers.add_parser("stats", help="print the corpus parse-rate scoreboard")
    stats.add_argument("root", type=Path, help="directory to scan for ini/inc/bhav files")
    stats.add_argument(
        "--overlay",
        type=Path,
        action="append",
        default=[],
        help="lower-priority ini root that includes may resolve into (repeatable)",
    )

    lint = subparsers.add_parser("lint", help="report parse/load/conversion problems")
    lint.add_argument("paths", type=Path, nargs="+", help="ini files or folders to assemble")

    xref = subparsers.add_parser("xref", help="show a definition's references, both directions")
    xref.add_argument("root", type=Path, help="folder of ini files to assemble")
    xref.add_argument("name", help="definition name to look up (e.g. GondorFighter)")

    args = parser.parse_args(argv)

    if args.command == "stats":
        if not args.root.is_dir():
            parser.error(f"not a directory: {args.root}")
        print(format_scoreboard(compute_scoreboard(args.root, overlays=tuple(args.overlay))))
        return 0

    if args.command == "lint":
        missing = [p for p in args.paths if not p.exists()]
        if missing:
            parser.error(f"no such file or directory: {missing[0]}")
        return _run_lint(args.paths)

    if args.command == "xref":
        if not args.root.is_dir():
            parser.error(f"not a directory: {args.root}")
        return _run_xref(args.root, args.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
