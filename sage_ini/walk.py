"""Traversal over the two sage_ini structures: `walk_nodes`/`walk_blocks` descend the
comment-preserving AST, `walk_objects` descends the typed `Game` (or any `IniObject`)."""

from collections.abc import Iterator

from sage_ini.model.game import Game
from sage_ini.model.objects import IniObject
from sage_ini.parser.ast import Block, IniDocument, Node

__all__ = ["walk_nodes", "walk_blocks", "walk_objects"]


def walk_nodes(root: IniDocument | Node) -> Iterator[Node]:
    """Every AST node under `root`, depth-first pre-order (a node yields itself, then a
    `Block`'s children). Script bodies are opaque, so a `ScriptBlock` has no child nodes."""
    if isinstance(root, IniDocument):
        for child in root.children:
            yield from walk_nodes(child)
        return
    yield root
    if isinstance(root, Block):
        for child in root.children:
            yield from walk_nodes(child)


def walk_blocks(root: IniDocument | Node, name: str | None = None) -> Iterator[Block]:
    """Every `Block` under `root`; with `name`, only blocks of that header name."""
    for node in walk_nodes(root):
        if isinstance(node, Block) and (name is None or node.name == name):
            yield node


def walk_objects(root: Game | IniObject, cls: type[IniObject] | None = None) -> Iterator[IniObject]:
    """Every typed object under `root`, depth-first (an `IniObject` yields itself, then its
    nested-group children and modules). With `cls`, only instances of that class."""
    for obj in _iter_objects(root):
        if cls is None or isinstance(obj, cls):
            yield obj


def _iter_objects(root: Game | IniObject) -> Iterator[IniObject]:
    if isinstance(root, Game):
        for table in root.tables.values():
            for obj in table.values():
                yield from _iter_objects(obj)
        return
    yield root
    for items in root._nested_data.values():
        for item in items:
            yield from _iter_objects(item)
    for module in root._modules:
        yield from _iter_objects(module)
