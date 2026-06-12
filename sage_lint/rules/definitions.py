"""Rules over the set of top-level definitions a game declares."""

from collections.abc import Iterator

from sage_ini.model.game import Game
from sage_ini.parser.diagnostics import Diagnostic, Severity
from sage_lint.rules.base import Rule


class DuplicateDefinitionRule(Rule):
    """A unique-named definition declared twice in one file (the engine keeps the last
    and drops the earlier, so a same-file repeat is almost always a copy-paste slip).
    Cross-file redefinitions (the override mechanism) and collection types are not
    recorded as redefinitions, so neither flags."""

    code = "duplicate-definition"

    def check(self, game: Game) -> Iterator[Diagnostic]:
        for redef in game.redefinitions:
            yield Diagnostic(
                code=self.code,
                message=(
                    f"{redef.name} is defined again here; the earlier definition at "
                    f"line {redef.first.line_start} is overwritten (last wins)"
                ),
                span=redef.second,
                severity=Severity.WARNING,
                extra={
                    "key": redef.key,
                    "name": redef.name,
                    "first_line": redef.first.line_start,
                },
            )
