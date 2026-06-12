"""SAGE ini parsing layer: text -> tokens -> comment-preserving AST.

Public entry points are re-exported here for convenience (`from sage_ini.parser import
parse, print_document`); each submodule also declares its own `__all__`."""

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
    line_count,
)
from sage_ini.parser.blockparser import ParseResult, parse, parse_file, parse_lines
from sage_ini.parser.diagnostics import Diagnostic, Diagnostics, Severity
from sage_ini.parser.io import INI_SUFFIXES, iter_ini_files, read_text
from sage_ini.parser.location import Span
from sage_ini.parser.printer import print_document

__all__ = [
    "parse",
    "parse_file",
    "parse_lines",
    "ParseResult",
    "print_document",
    "Diagnostic",
    "Diagnostics",
    "Severity",
    "Span",
    "IniDocument",
    "Node",
    "Block",
    "Attribute",
    "Comment",
    "BlankLine",
    "MacroDef",
    "Include",
    "ScriptBlock",
    "line_count",
    "read_text",
    "iter_ini_files",
    "INI_SUFFIXES",
]
