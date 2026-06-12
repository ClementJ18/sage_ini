"""Import side effect: importing the definition modules runs their class bodies, so each
`IniObject` subclass registers itself by name. `Game.load_document` imports this first.
"""

from sage_ini.model import (  # noqa: F401  (registration)
    behaviors,
    data_blocks,
    draw,
    fxlist,
    ini_objects,
    livingworld,
    misc_blocks,
    nuggets,
    particles,
    ui,
)
