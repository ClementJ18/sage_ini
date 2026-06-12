"""Rule: every referenced localization label must resolve in the string table."""

from collections.abc import Iterator

from sage_ini.model.game import Game
from sage_ini.model.objects import resolve_annotation
from sage_ini.model.types import Label
from sage_ini.parser.diagnostics import Diagnostic, Severity
from sage_ini.suggest import suggestion_hint
from sage_ini.walk import walk_objects
from sage_lint.rules.base import Rule

# `Label` is a typed alias (`Annotated[str, converter]`); the converter is what a field's
# resolved annotation actually is, so compare against that, not the alias.
_LABEL = resolve_annotation(Label)


def _is_label(obj, key: str) -> bool:
    """Whether `key` is a `Label` field, matching both a scalar `Label` and a
    `List[Label]` (a button's per-state `TextLabel`/`DescriptLabel`)."""
    fieldspec = type(obj)._fieldspec
    if key not in fieldspec:
        return False
    try:
        annotation = resolve_annotation(fieldspec[key])
    except KeyError:
        return False
    if annotation is _LABEL:
        return True
    element = getattr(annotation, "element", None)
    return element is not None and resolve_annotation(element) is _LABEL


class UnknownStringLabelRule(Rule):
    """A `Label` field naming a string the loaded table does not define (it shows in-game
    as its raw name — a content bug). Lookups are case-insensitive; each `NAMESPACE:key`
    token of a multi-label value is checked, tokens without a `:` left alone. Skipped when
    no string table was loaded, else every label would falsely flag."""

    code = "unknown-string-label"

    def check(self, game: Game) -> Iterator[Diagnostic]:
        if not game.strings:
            return
        known = {label.lower() for label in game.strings}
        for obj in walk_objects(game):
            for key, value in obj.fields.items():
                if not _is_label(obj, key):
                    continue
                entries = value if isinstance(value, list) else [value]
                for entry in entries:
                    if not isinstance(entry, str):
                        continue
                    for token in entry.split():
                        if ":" not in token or token.lower() in known:
                            continue
                        # Restrict candidates to the token's own namespace so a typo in the
                        # key is matched against sibling labels, not every string in the game.
                        namespace = token.split(":", 1)[0].lower()
                        siblings = [
                            label
                            for label in game.strings
                            if label.split(":", 1)[0].lower() == namespace
                        ]
                        hint, suggestion = suggestion_hint(token, siblings)
                        yield Diagnostic(
                            code=self.code,
                            message=(
                                f"{type(obj).__name__}.{key} references string {token!r}, "
                                f"which the string table does not define.{hint}"
                            ),
                            span=obj._field_spans.get(key, obj.span),
                            severity=Severity.WARNING,
                            extra={
                                "label": token,
                                "type": type(obj).__name__,
                                "key": key,
                                "suggestion": suggestion,
                            },
                        )
