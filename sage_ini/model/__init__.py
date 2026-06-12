"""Typed game-element model built on the parser AST (objects, enums, converters).

The core entry points are re-exported here. The game-schema classes themselves (`Object`,
`Weapon`, the behavior modules, …) live in their topic modules (`ini_objects`, `behaviors`,
`data_blocks`, …) and are reached by name through `get_class`/`REGISTRY` or imported from
those modules directly; they are part of the public surface but versioned additively (new
fields are added over time)."""

from sage_ini.model.game import Game, Redefinition
from sage_ini.model.objects import (
    REGISTRY,
    Behavior,
    Draw,
    IniObject,
    Module,
    NestedAttribute,
    Nugget,
    classify_subblock,
    get_class,
    resolve_annotation,
)
from sage_ini.model.xref import Xref

__all__ = [
    "Game",
    "Redefinition",
    "IniObject",
    "Module",
    "NestedAttribute",
    "Nugget",
    "Behavior",
    "Draw",
    "REGISTRY",
    "get_class",
    "resolve_annotation",
    "classify_subblock",
    "Xref",
]
