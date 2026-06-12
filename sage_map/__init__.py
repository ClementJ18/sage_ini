"""Game-aware typed overlay over the `sagemap` binary `.map` parser.

`sagemap` parses a WorldBuilder `.map` into dataclasses, but its script arguments and object
references are only weakly typed: an argument knows it is a string, not that the string must name
a defined Object, Science or map-local team. This package attaches that meaning — mapping each
value to the scope it must resolve against (a definition in the assembled `Game`, a symbol the map
itself defines, or a closed enum) — so a map can be linted the way `sage_lint` lints ini files.

v1 covers script-argument and object references only; object-property typing and the
`content_type` action table are deferred. See docs/sage_map_plan.md.
"""

from sage_map.linter import lint_map, lint_map_file, lint_maps
from sage_map.model import (
    MapModel,
    MapSymbols,
    ScriptArgRef,
    build_symbols,
    iter_script_arguments,
)
from sage_map.scripts import (
    ARG_SPECS,
    ArgSpec,
    ResolvedArg,
    Scope,
    arg_spec,
    typed_value,
)

__all__ = [
    "ARG_SPECS",
    "ArgSpec",
    "MapModel",
    "MapSymbols",
    "ResolvedArg",
    "Scope",
    "ScriptArgRef",
    "arg_spec",
    "build_symbols",
    "iter_script_arguments",
    "lint_map",
    "lint_map_file",
    "lint_maps",
    "typed_value",
]
