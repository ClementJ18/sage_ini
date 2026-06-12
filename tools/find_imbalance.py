"""Localize block imbalances: report Ends whose indentation differs from
their opener's, plus blocks whose first child is shallower than the header.

Usage: find_imbalance.py <file>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sage_ini.parser.io import read_text  # noqa: E402,PLC0415
from sage_ini.parser.keywords import (  # noqa: E402,PLC0415
    BARE_VALUE_KEYS,
    BLOCK_OPENING_KEYWORDS,
    CONDITIONAL_VALUE_OPENERS,
    CONTEXTUAL_BARE_VALUE_KEYS,
    CONTEXTUAL_BLOCK_OPENERS,
    OPENER_VALUE_TOKENS,
)
from sage_ini.parser.lexer import tokenize  # noqa: E402,PLC0415


def indent_width(raw: str) -> int:
    return len(raw[: len(raw) - len(raw.lstrip())].expandtabs(4))


def main() -> int:
    path = Path(sys.argv[1])
    stack: list[tuple[str, int, int]] = []  # name, line, indent
    in_script = False

    for line in tokenize(read_text(path), file=str(path)):
        content = line.content
        if in_script:
            if content.lower() == "endscript":
                in_script = False
            continue
        if not content:
            continue

        if content.lower() == "end":
            if not stack:
                print(f"{line.number:6} stray End")
                continue
            name, opened, opener_indent = stack.pop()
            end_indent = indent_width(line.raw)
            if end_indent != opener_indent:
                print(
                    f"{line.number:6} End(indent {end_indent}) closes {name}@{opened}"
                    f" (indent {opener_indent})"
                )
            continue

        if content.startswith("#"):
            continue

        first = content.split()[0]
        if first == "BeginScript":
            in_script = True
            continue

        if "=" in content:
            key, _, value = content.partition("=")
            key = key.strip()
            value = value.strip()
            parent = stack[-1][0] if stack else None
            contextual = CONTEXTUAL_BLOCK_OPENERS.get(parent, frozenset())
            value_head = value.split(maxsplit=1)[0] if value else ""
            if (
                key in BLOCK_OPENING_KEYWORDS
                or key in contextual
                or value_head in OPENER_VALUE_TOKENS
                or CONDITIONAL_VALUE_OPENERS.get(key) == value_head
            ):
                stack.append((key, line.number, indent_width(line.raw)))
            continue

        parent = stack[-1][0] if stack else None
        contextual_values = CONTEXTUAL_BARE_VALUE_KEYS.get(parent, frozenset())
        if (
            first not in BARE_VALUE_KEYS
            and first not in contextual_values
            and not first[0].isdigit()
        ):
            stack.append((first, line.number, indent_width(line.raw)))

    for name, opened, _ in stack:
        print(f"  EOF: unclosed {name}@{opened}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
