"""Canonical printer: AST -> text with logical indentation and all comments. Contract:
`parse(print_document(doc))` yields a tree equal to `doc`, and reprinting is a fixed point.

`align_equals` is an optional cosmetic mode: the `=` of attribute assignments are aligned by
padding each key out to the widest in its group. Groups are runs of sibling lines split by
blank lines, so visually separated sections align independently. `align_exclude` names block
types whose attributes are left unaligned. The parser strips whitespace around `=`, so the
padding is purely visual and the round-trip still holds.
"""

from collections.abc import Iterable

from sage_ini.parser.ast import (
    Attribute,
    BlankLine,
    Block,
    Comment,
    Include,
    IniDocument,
    MacroDef,
    Node,
    ScriptBlock,
)

__all__ = ["print_document", "INDENT"]

INDENT = "    "


def _suffix(comment: str | None) -> str:
    return f" {comment}" if comment else ""


def _block_type_tokens(block: Block) -> set[str]:
    """The identifiers naming a block's type, casefolded: its header keyword (`Object`,
    `ArmorSet`, `Draw`, `Behavior`…) and, for a module-style header, the module subtype that
    leads its label (`ActiveBody` in `Behavior = ActiveBody ModuleTag_01`). Either spelling
    can be named in `align_exclude`."""
    tokens = {block.name.casefold()}
    if block.label:
        tokens.add(block.label.split()[0].casefold())
    return tokens


def _group_widths(children: list[Node], align: bool) -> list[int]:
    """Per-child key column widths for `=` alignment, one entry per child (0 = pad nothing).
    Each group of consecutive non-blank siblings shares the width of its widest attribute
    assignment; a blank line ends a group so sections align independently. Bare-value lines
    (no `=`) and nested blocks never widen a column."""
    widths = [0] * len(children)
    if not align:
        return widths
    group: list[int] = []

    def flush() -> None:
        width = max(
            (
                len(child.key)
                for child in (children[i] for i in group)
                if isinstance(child, Attribute) and child.uses_equals
            ),
            default=0,
        )
        for i in group:
            widths[i] = width

    for index, child in enumerate(children):
        if isinstance(child, BlankLine):
            flush()
            group = []
        else:
            group.append(index)
    flush()
    return widths


def _emit(node: Node, depth: int, out: list[str], align: bool, exclude: frozenset[str], width=0):
    pad = INDENT * depth

    match node:
        case BlankLine():
            out.append("")
        case Comment(text=text):
            out.append(f"{pad}{text}")
        case MacroDef(name=name, value=value, comment=comment):
            line = f"{pad}#define {name} {value}" if value else f"{pad}#define {name}"
            out.append(line + _suffix(comment))
        case Include(path=path, comment=comment):
            out.append(f'{pad}#include "{path}"' + _suffix(comment))
        case Attribute(key=key, value=value, uses_equals=True, comment=comment):
            field = key.ljust(width)  # ljust is a no-op when width is 0 (align off / excluded)
            line = f"{pad}{field} = {value}" if value else f"{pad}{field} ="
            out.append(line + _suffix(comment))
        case Attribute(key=key, value=value, comment=comment):
            line = f"{pad}{key} {value}" if value else f"{pad}{key}"
            out.append(line + _suffix(comment))
        case ScriptBlock():
            out.append(f"{pad}BeginScript" + _suffix(node.comment))
            out.extend(node.lines)
            out.append(f"{pad}EndScript" + _suffix(node.end_comment))
        case Block():
            header = node.name
            if node.uses_equals:
                header += f" = {node.label}" if node.label else " ="
            elif node.label:
                header += f" {node.label}"
            out.append(f"{pad}{header}" + _suffix(node.comment))
            # A block named in `align_exclude` has its own attributes left unaligned; nested
            # blocks are still judged on their own type.
            child_align = align and not (exclude & _block_type_tokens(node))
            _emit_children(node.children, depth + 1, out, align, exclude, child_align)
            out.append(f"{pad}End" + _suffix(node.end_comment))


def _emit_children(
    children: list[Node],
    depth: int,
    out: list[str],
    align: bool,
    exclude: frozenset[str],
    aligned: bool,
):
    """Emit a block's (or the document's) children, aligning `=` per blank-line-delimited
    group when `aligned`. `align`/`exclude` carry through so nested blocks align in turn."""
    widths = _group_widths(children, aligned)
    for index, child in enumerate(children):
        _emit(child, depth, out, align, exclude, widths[index])


def print_document(
    document: IniDocument,
    *,
    align_equals: bool = False,
    align_exclude: Iterable[str] = (),
) -> str:
    exclude = frozenset(token.casefold() for token in align_exclude)
    out: list[str] = []
    _emit_children(document.children, 0, out, align_equals, exclude, align_equals)
    return "\n".join(out) + "\n" if out else ""
