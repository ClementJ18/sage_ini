"""One-off analysis: vocabulary of bare content lines (no '=') in the corpora.

For each distinct first token of a bare line, guess opener-vs-value by
checking whether a later line in the same file is exactly `End` more often
than the token count would allow if they were values; the real signal printed
is per-token sample lines for manual classification.

Usage: python tools/scan_bare_lines.py <root> [<root> ...]
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sage_ini.parser.io import iter_ini_files, read_text  # noqa: E402,PLC0415
from sage_ini.parser.lexer import tokenize  # noqa: E402,PLC0415


def main() -> int:
    counts = Counter()
    samples: dict[str, str] = {}
    files: dict[str, set] = defaultdict(set)

    for root in (Path(p) for p in sys.argv[1:]):
        for path in iter_ini_files(root):
            for line in tokenize(read_text(path), file=str(path)):
                content = line.content
                if not content or "=" in content or content.lower() == "end":
                    continue
                if content.startswith("#"):
                    continue
                token = content.split()[0]
                counts[token] += 1
                samples.setdefault(token, content[:90])
                files[token].add(path.name)

    print(f"distinct bare first tokens: {len(counts)}")
    for token, count in counts.most_common():
        in_files = len(files[token])
        print(f"{count:7}  {token:42} files={in_files:4}  e.g. {samples[token]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
