"""AST node types for SAGE ini documents. Comment-preserving but not byte-faithful
(whitespace is not stored). Node equality ignores spans, so a reprinted-and-reparsed
document compares equal to the original (the round-trip contract).
"""

from dataclasses import dataclass, field

from sage_ini.parser.location import Span

__all__ = [
    "BlankLine",
    "Comment",
    "Attribute",
    "ScriptBlock",
    "MacroDef",
    "Include",
    "Block",
    "Node",
    "IniDocument",
    "line_count",
]


@dataclass(slots=True, kw_only=True)
class BlankLine:
    """A blank-line separator between siblings. Runs collapse to one, and none survive at
    a block's or the document's edges, so the tree stays canonical."""

    span: Span = field(compare=False)


@dataclass(slots=True, kw_only=True)
class Comment:
    """A line that contains only a comment."""

    text: str  # original comment text including its marker
    span: Span = field(compare=False)


@dataclass(slots=True, kw_only=True)
class Attribute:
    key: str
    value: str  # raw value text, untyped; "" when the line is `Key =`
    uses_equals: bool = True  # False for bare value lines (`ParticleSysBone NONE X`)
    comment: str | None = None  # trailing comment sharing the line
    span: Span = field(compare=False)


@dataclass(slots=True, kw_only=True)
class ScriptBlock:
    """`BeginScript ... EndScript`: an opaque Lua body stored verbatim, so Lua's own `end`
    never closes an ini block."""

    lines: list[str]  # raw body lines, verbatim (blanks included)
    comment: str | None = None  # trailing comment on the BeginScript line
    end_comment: str | None = None  # trailing comment on the EndScript line
    span: Span = field(compare=False)


@dataclass(slots=True, kw_only=True)
class MacroDef:
    name: str
    value: str
    comment: str | None = None
    span: Span = field(compare=False)


@dataclass(slots=True, kw_only=True)
class Include:
    path: str  # as written, without the surrounding quotes
    comment: str | None = None
    span: Span = field(compare=False)


@dataclass(slots=True, kw_only=True)
class Block:
    name: str  # first header token: "Object", "Behavior", "LodOptions", ...
    label: str | None  # remainder of the header, e.g. "MordorFighter" or "LOW"
    uses_equals: bool  # header was `Name = Label` rather than `Name Label`
    children: list["Node"] = field(default_factory=list)
    comment: str | None = None  # trailing comment on the header line
    end_comment: str | None = None  # trailing comment on the End line
    span: Span = field(compare=False)


Node = BlankLine | Comment | Attribute | MacroDef | Include | Block | ScriptBlock


@dataclass(slots=True, kw_only=True)
class IniDocument:
    file: str
    children: list[Node] = field(default_factory=list)
    span: Span = field(compare=False)


def line_count(nodes: list[Node]) -> int:
    """Number of non-blank source lines the nodes account for (a block contributes
    header + End; a script block its delimiters plus non-blank body lines)."""
    total = 0
    for node in nodes:
        if isinstance(node, BlankLine):
            continue
        if isinstance(node, Block):
            total += 2 + line_count(node.children)
        elif isinstance(node, ScriptBlock):
            total += 2 + sum(1 for raw in node.lines if raw.strip())
        else:
            total += 1
    return total
