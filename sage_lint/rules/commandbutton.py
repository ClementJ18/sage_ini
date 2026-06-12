"""Rules specific to CommandButton definitions."""

from collections.abc import Iterator

from sage_ini.model.game import Game
from sage_ini.parser.diagnostics import Diagnostic, Severity
from sage_lint.rules.base import Rule

# The None/NONE/empty sentinels Nullable resolves to None (mirrors types._Nullable.convert).
_NONE_SENTINELS = frozenset({"", "none"})

# CommandButton reference fields whose default is already "no target", so an explicit
# None/NONE merely restates the default.
_NULLABLE_DEFAULT_FIELDS = ("Object", "SpecialPower")


def _is_none_sentinel(value) -> bool:
    return isinstance(value, str) and value.strip().lower() in _NONE_SENTINELS


class RedundantNullificationRule(Rule):
    """A CommandButton `Object` or `SpecialPower` written as `None`/`NONE`. Both fields default
    to "no target" when the key is absent, so explicitly nullifying them changes nothing — the
    engine accepts it, but it is dead clutter (usually a copy-paste leftover from a template
    button). The value stays valid; this only flags the redundancy so it can be removed."""

    code = "redundant-nullification"

    def check(self, game: Game) -> Iterator[Diagnostic]:
        for button in game.commandbuttons.values():
            fields = button.fields
            for key in _NULLABLE_DEFAULT_FIELDS:
                value = fields.get(key)
                if isinstance(value, list):
                    value = value[-1]  # a repeated scalar keeps only its last occurrence
                if not _is_none_sentinel(value):
                    continue
                yield Diagnostic(
                    code=self.code,
                    message=(
                        f"CommandButton.{key} is set to None, which is already the default; "
                        "the nullification is redundant."
                    ),
                    span=button._field_spans.get(key, button.span),
                    severity=Severity.WARNING,
                    extra={"type": "CommandButton", "key": key, "name": button.name},
                )
