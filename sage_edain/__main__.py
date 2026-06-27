"""Command-line entry point: `python -m sage_edain <command>` (or `sage-edain`).

- `factions <dir>` — list the playable factions in a mod.
- `explore <dir> <faction>` — print (or `--json`) the faction's ownership graph: its spellbook,
  start points, base structures, and the units / heroes / upgrades they produce.
- `serve <dir> <faction>` — open a small web UI (sage_edain/ui) to traverse that graph.

`<dir>` is the mod's ini root (e.g. `_mod/data/ini`). Pass `--bases` (the mod's `bases/` folder) to
decompose castle/camp layouts into their citadel + foundations + prebuilt structures (needs the
`[edain]` extra). `--base` layers a base-game ini source for completeness, like `sage_lint`.
"""

import argparse
import json
from pathlib import Path

from sage_edain.graph import (
    build_faction_graph,
    build_faction_graphs,
    find_faction,
    playable_factions,
)
from sage_edain.model import FactionGraph
from sage_ini.loader import load_game


def _load(root: Path, base: list[Path]):
    """Assemble the game from `root`, layering any `--base` sources for completeness.

    Point `root` at the **mod folder** (e.g. `_mod`): the loader scans it recursively for ini *and*
    for the localization table (`Lotr.csv` / `.str`), so display names resolve to their in-game
    text. Passing the deeper ini folder (`_mod/data/ini`) still works but misses the string table,
    which lives above it — names then fall back to raw template ids."""
    return load_game(root, bases=tuple(base)).game


def _default_bases_dir(root: Path) -> Path | None:
    """Find the mod's `bases/` folder relative to `root` — `root/bases` when `root` is the mod
    folder, else the nearest ancestor that holds one."""
    for folder in (root, *root.parents):
        candidate = folder / "bases"
        if candidate.is_dir():
            return candidate
    return None


def _run_factions(root: Path, base: list[Path]) -> int:
    game = _load(root, base)
    factions = playable_factions(game)
    if not factions:
        print(f"no playable factions found under {root}")
        return 1
    for faction in factions:
        side = faction._fields.get("Side")
        side = side[-1] if isinstance(side, list) else side
        print(f"{faction.name}\t[{side}]")
    return 0


def _print_graph(graph: FactionGraph) -> None:
    print(f"{graph.display}  ({graph.name}, side={graph.side})")
    if graph.spellbook:
        print(f"\nSpellbook: {graph.spellbook.name}")
        for power in graph.spellbook.powers:
            cd = f"  [{power.cooldown:g}s]" if power.cooldown else ""
            print(f"  - {power.display}{cd}")
    print("\nStart points:")
    for point in graph.start_points:
        target = point.base or point.structure or "?"
        print(f"  - {point.flag} ({point.kind.value}) -> {target}")
        if point.citadel:
            print(f"      citadel: {point.citadel}")
        if point.foundations:
            print(f"      foundations: {', '.join(point.foundations)}")
        if point.prebuilt:
            print(f"      prebuilt: {', '.join(point.prebuilt)}")
    print(f"\nStructures ({len(graph.structures)}):")
    for structure in graph.structures.values():
        bits = []
        if structure.trains_units:
            bits.append(f"{len(structure.trains_units)} units")
        if structure.recruits_heroes:
            bits.append(f"{len(structure.recruits_heroes)} heroes")
        if structure.researches_upgrades:
            bits.append(f"{len(structure.researches_upgrades)} upgrades")
        summary = f" ({', '.join(bits)})" if bits else ""
        print(f"  - [{structure.role.value}] {structure.display}{summary}")
    print(f"\nUnits ({len(graph.units)}):")
    for unit in graph.units.values():
        print(f"  - {unit.display}")
    print(f"\nHeroes ({len(graph.heroes)}):")
    for hero in graph.heroes.values():
        print(f"  - {hero.display}")
    print(f"\nUpgrades ({len(graph.upgrades)}):")
    for upgrade in graph.upgrades.values():
        print(f"  - {upgrade.display}")


def _print_summary(graph: FactionGraph) -> None:
    """A one-line per-faction tally, for the all-factions text view."""
    print(
        f"{graph.display} ({graph.name}, {graph.side}): "
        f"{len(graph.structures)} structures, {len(graph.units)} units, "
        f"{len(graph.heroes)} heroes, {len(graph.upgrades)} upgrades"
    )


def _build_graphs(root: Path, faction_name, base: list[Path], bases_dir):
    """The graphs to act on, or None on error. `faction_name` None builds every playable faction;
    a name/Side builds just that one."""
    game = _load(root, base)
    resolved_bases = bases_dir if bases_dir is not None else _default_bases_dir(root)
    if faction_name is None:
        graphs = build_faction_graphs(game, resolved_bases)
        if not graphs:
            print(f"no playable factions found under {root}")
            return None
        return graphs
    faction = find_faction(game, faction_name)
    if faction is None:
        names = ", ".join(f.name for f in playable_factions(game))
        print(f"no playable faction matching {faction_name!r}; choose one of: {names}")
        return None
    return [build_faction_graph(game, faction, resolved_bases)]


def _payload(graphs: list[FactionGraph], all_factions: bool) -> dict:
    """The JSON the UI consumes: a single graph dict, or a `{"factions": [...]}` wrapper the UI
    turns into a faction picker."""
    if all_factions:
        return {"factions": [graph.to_dict() for graph in graphs]}
    return graphs[0].to_dict()


def _run_explore(root: Path, faction_name, base: list[Path], bases_dir, as_json: bool) -> int:
    graphs = _build_graphs(root, faction_name, base, bases_dir)
    if graphs is None:
        return 1
    all_factions = faction_name is None
    if as_json:
        print(json.dumps(_payload(graphs, all_factions), indent=2))
    elif all_factions:
        for graph in graphs:
            _print_summary(graph)
    else:
        _print_graph(graphs[0])
    return 0


def _run_serve(root, faction_name, base, bases_dir, port, open_browser) -> int:
    from sage_edain.server import serve  # noqa: PLC0415 — only needed for `serve`

    graphs = _build_graphs(root, faction_name, base, bases_dir)
    if graphs is None:
        return 1
    all_factions = faction_name is None
    label = f"{len(graphs)} factions" if all_factions else (graphs[0].display or graphs[0].name)
    serve(_payload(graphs, all_factions), label, port=port, open_browser=open_browser)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sage_edain")
    subparsers = parser.add_subparsers(dest="command", required=True)

    factions = subparsers.add_parser("factions", help="list a mod's playable factions")
    factions.add_argument("root", type=Path, help="the mod's ini root (e.g. _mod/data/ini)")
    factions.add_argument("--base", type=Path, action="append", default=[], help="base-game ini")

    explore = subparsers.add_parser("explore", help="print a faction's ownership graph")
    explore.add_argument("root", type=Path, help="the mod folder (e.g. _mod)")
    explore.add_argument(
        "faction",
        nargs="?",
        default=None,
        help="faction template name or Side token (e.g. Gondor); omit for all playable factions",
    )
    explore.add_argument("--base", type=Path, action="append", default=[], help="base-game ini")
    explore.add_argument(
        "--bases", type=Path, default=None, help="the mod's bases/ folder (base-layout .bse files)"
    )
    explore.add_argument("--json", action="store_true", help="emit the graph as JSON")

    serve = subparsers.add_parser("serve", help="open a web UI to traverse a faction's graph")
    serve.add_argument("root", type=Path, help="the mod folder (e.g. _mod)")
    serve.add_argument(
        "faction",
        nargs="?",
        default=None,
        help="faction template name or Side token; omit to serve all factions with a picker",
    )
    serve.add_argument("--base", type=Path, action="append", default=[], help="base-game ini")
    serve.add_argument("--bases", type=Path, default=None, help="the mod's bases/ folder")
    serve.add_argument("--port", type=int, default=8765, help="localhost port (default: 8765)")
    serve.add_argument("--no-browser", action="store_true", help="do not open a browser")

    args = parser.parse_args(argv)

    if args.command == "factions":
        if not args.root.is_dir():
            parser.error(f"not a directory: {args.root}")
        return _run_factions(args.root, args.base)

    if args.command == "explore":
        if not args.root.is_dir():
            parser.error(f"not a directory: {args.root}")
        return _run_explore(args.root, args.faction, args.base, args.bases, args.json)

    if args.command == "serve":
        if not args.root.is_dir():
            parser.error(f"not a directory: {args.root}")
        return _run_serve(
            args.root, args.faction, args.base, args.bases, args.port, not args.no_browser
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
