"""The cross-reference graph: a field resolving to another registered object is an edge.
`Xref` drives that resolution once over the whole game and records both directions, so a
consumer can ask what an object references (forward) or what references it (reverse). The
nodes are the registered objects; references anywhere inside an object's subtree are
attributed to it.
"""

import enum
from collections import defaultdict
from collections.abc import Iterator

from sage_ini.model.game import Game
from sage_ini.model.objects import IniObject
from sage_ini.walk import walk_objects

__all__ = ["Xref"]

# Converted values that hold no reference and must not be descended into.
_SCALAR = (str, bytes, bool, int, float, enum.Enum)


def _registered(game: Game, obj: IniObject) -> bool:
    """Whether `obj` is the object registered under its (key, name) in the game."""
    return obj.key is not None and game.tables.get(obj.key, {}).get(obj.name) is obj


def _referenced_objects(value, game: Game, seen: set[int]) -> Iterator[IniObject]:
    """Every registered object reachable inside a converted field value (which may be an
    object, a container of them, or a converter object holding them as attributes). Descent
    stops at a registered object (an edge endpoint) and at scalars/enums."""
    if isinstance(value, _SCALAR) or value is None:
        return
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, IniObject):
        if _registered(game, value):
            yield value  # an edge endpoint; its own fields are its own node's edges
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _referenced_objects(item, game, seen)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _referenced_objects(item, game, seen)
    elif hasattr(value, "__dict__"):
        # A converter object holds its references as instance attributes.
        for item in vars(value).values():
            yield from _referenced_objects(item, game, seen)


class Xref:
    """The forward/reverse reference graph of a loaded `Game`, built once."""

    def __init__(self, game: Game):
        self.game = game
        self._forward: dict[IniObject, set[IniObject]] = defaultdict(set)
        self._reverse: dict[IniObject, set[IniObject]] = defaultdict(set)
        self._build()

    def _build(self) -> None:
        for table in self.game.tables.values():
            for root in table.values():
                for target in self._references_of(root):
                    self._forward[root].add(target)
                    self._reverse[target].add(root)

    def _references_of(self, root: IniObject) -> set[IniObject]:
        """The registered objects referenced anywhere in `root`'s subtree (not self)."""
        found: set[IniObject] = set()
        for node in walk_objects(root):
            fieldspec = type(node)._fieldspec
            for key in node.fields:
                if key not in fieldspec:
                    continue
                try:
                    value = getattr(node, key)
                except (ValueError, KeyError, TypeError, IndexError):
                    continue  # a bad value is the validate/lint pass's diagnostic
                found.update(_referenced_objects(value, self.game, set()))
        found.discard(root)
        return found

    def references(self, obj: IniObject) -> frozenset[IniObject]:
        """The objects `obj` references (forward edges)."""
        return frozenset(self._forward.get(obj, ()))

    def referenced_by(self, obj: IniObject) -> frozenset[IniObject]:
        """The objects that reference `obj` (reverse edges)."""
        return frozenset(self._reverse.get(obj, ()))

    def is_referenced(self, obj: IniObject) -> bool:
        """Whether anything references `obj`."""
        return bool(self._reverse.get(obj))
