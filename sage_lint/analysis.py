"""Meta-analysis over a loaded game: per-faction stats (unit counts and costs) and
mod-vs-base table diffs. Reads the typed model through the walker; never mutates it."""

from collections import defaultdict
from dataclasses import dataclass

from sage_ini.model.game import Game
from sage_ini.model.objects import IniObject
from sage_ini.walk import walk_objects

_NO_SIDE = "<none>"


def _side(obj: IniObject) -> str:
    """An object's faction side as a plain string, or `<none>` when it has none."""
    try:
        value = obj.Side if "Side" in obj.fields else None
    except (ValueError, KeyError, TypeError, IndexError):
        return _NO_SIDE
    if value is None:
        return _NO_SIDE
    return getattr(value, "name", None) or str(value)


def _cost(obj: IniObject) -> int:
    """An object's `BuildCost`, or 0 when absent or unconvertible."""
    try:
        return int(obj.BuildCost or 0) if "BuildCost" in obj.fields else 0
    except (ValueError, KeyError, TypeError, IndexError):
        return 0


@dataclass(frozen=True, slots=True)
class FactionStats:
    """How many objects a side fields and what the priced ones cost."""

    side: str
    objects: int  # every object on the side
    buildable: int  # those with a positive BuildCost
    total_cost: int
    average_cost: float  # mean over the buildable ones (0.0 when none)


def faction_stats(game: Game) -> dict[str, FactionStats]:
    """Per-side object and cost stats over the game's `objects` table."""
    by_side: dict[str, list[IniObject]] = defaultdict(list)
    for obj in game.objects.values():
        by_side[_side(obj)].append(obj)

    stats: dict[str, FactionStats] = {}
    for side, objects in by_side.items():
        costs = [cost for obj in objects if (cost := _cost(obj)) > 0]
        total = sum(costs)
        stats[side] = FactionStats(
            side=side,
            objects=len(objects),
            buildable=len(costs),
            total_cost=total,
            average_cost=total / len(costs) if costs else 0.0,
        )
    return stats


def cost_curve(game: Game, side: str | None = None) -> list[tuple[str, int]]:
    """`(name, BuildCost)` for priced objects, dearest first (optionally one side)."""
    curve = [
        (obj.name, cost)
        for obj in game.objects.values()
        if (side is None or _side(obj) == side) and (cost := _cost(obj)) > 0
    ]
    curve.sort(key=lambda item: (-item[1], item[0]))
    return curve


def _fingerprint(obj: IniObject) -> tuple:
    """A comparable snapshot of an object's whole subtree of raw fields, so a change to
    a nested behavior counts as a modification, not just a top-level edit."""
    return tuple(
        (
            type(node).__name__,
            node.name,
            tuple(
                sorted(
                    (key, tuple(value) if isinstance(value, list) else value)
                    for key, value in node.fields.items()
                )
            ),
        )
        for node in walk_objects(obj)
    )


@dataclass(frozen=True, slots=True)
class TableDiff:
    """The names a mod adds, drops, and changes in one table relative to a base."""

    key: str
    new: list[str]  # in the mod, not the base
    deleted: list[str]  # in the base, not the mod
    modified: list[str]  # in both, with differing content


def diff_table(base: Game, mod: Game, key: str) -> TableDiff:
    """Diff one table (`objects`, `weapons`, …) of `mod` against `base`. Objects in both
    are compared by their full subtree of raw fields (`_fingerprint`)."""
    base_table = base.tables.get(key, {})
    mod_table = mod.tables.get(key, {})
    new = [name for name in mod_table if name not in base_table]
    deleted = [name for name in base_table if name not in mod_table]
    modified = [
        name
        for name in base_table
        if name in mod_table and _fingerprint(base_table[name]) != _fingerprint(mod_table[name])
    ]
    return TableDiff(key=key, new=sorted(new), deleted=sorted(deleted), modified=sorted(modified))
