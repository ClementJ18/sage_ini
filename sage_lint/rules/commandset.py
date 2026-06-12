"""Rule: a CommandSet slot pointing at a CommandButton the game never defines."""

from collections.abc import Iterator

from sage_ini.model.game import Game
from sage_ini.parser.diagnostics import Diagnostic, Severity
from sage_ini.suggest import suggestion_hint
from sage_lint.rules.base import Rule

# An empty slot is written `NONE` (or left blank); that is the engine's "no button here", not
# a dangling reference, so it is never flagged.
_NONE_SENTINELS = frozenset({"", "none"})


class CommandSetButtonRule(Rule):
    """A numbered CommandSet slot (`3 = Command_Foo`) naming a CommandButton no definition
    declares: in-game the slot is empty — the button silently never appears — a content bug,
    usually a typo or a button renamed in one place but not the other. `NONE` slots are the
    engine's "no button here" and are left alone. CommandButtons are always defined in the
    data, so unlike art/audio references this resolves authoritatively (WARNING, not INFO)."""

    code = "dangling-commandbutton"

    def check(self, game: Game) -> Iterator[Diagnostic]:
        buttons = game.commandbuttons
        for commandset in game.commandsets.values():
            for slot, value in commandset._fields.items():
                if not slot.isdigit():
                    continue
                if isinstance(value, list):
                    value = value[-1]  # a repeated slot keeps only its last button
                if not isinstance(value, str) or value.strip().lower() in _NONE_SENTINELS:
                    continue
                name = value.strip()
                if game.lookup("commandbuttons", name)[0] is not None:
                    continue  # resolves (case-insensitively, the way the engine looks it up)
                hint, suggestion = suggestion_hint(name, buttons)
                yield Diagnostic(
                    code=self.code,
                    message=(
                        f"CommandSet {commandset.name!r} slot {slot} references CommandButton "
                        f"{name!r}, which no definition declares.{hint}"
                    ),
                    span=commandset._field_spans.get(slot, commandset.span),
                    severity=Severity.WARNING,
                    extra={
                        "name": name,
                        "table": "commandbuttons",
                        "type": "CommandSet",
                        "key": slot,
                        "suggestion": suggestion,
                    },
                )
