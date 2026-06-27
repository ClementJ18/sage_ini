"""Assembling a faction's explicit ownership graph from a loaded `Game` (+ the mod's base
layouts).

The link is built outward from the `PlayerTemplate`:

1. **Spellbook** — the faction's `SpellBookMp`/`SpellBook` object, whose command set exposes its
   powers (SPELL_BOOK / SPECIAL_POWER buttons).
2. **Start points** — every plot flag whose `CastleBehavior.CastleToUnpackForFaction` names this
   faction's `Side`. Each names a base layout (resolved through `sage_edain.bases`) or a single
   structure.
3. **Base decomposition** — the layout's placed citadel, foundations and prebuilt structures.
4. **Producers** — a breadth-first walk from those structures over their command sets: `UNIT_BUILD`
   buttons that build a structure extend the walk (foundation buildings, expansions); buttons that
   build a unit, `REVIVE` heroes (index-based) and upgrade buttons become the graph's leaves, each
   carrying a `Producer` edge back to the building that yields it.

Everything is resolved through the existing typed-model helpers (`sage_utils.views`,
`sage_ini.model.state`); this module only orchestrates them into the graph shape.
"""

from __future__ import annotations

from pathlib import Path

from sage_edain.bases import resolve_base_layout
from sage_edain.model import (
    CreatedObject,
    FactionGraph,
    Power,
    ProducedUnit,
    Producer,
    RecruitedHero,
    ResearchableUpgrade,
    Spellbook,
    StartPoint,
    StartPointKind,
    Structure,
    StructureRole,
)
from sage_edain.powers import resolve_power
from sage_edain.profile import build_profile
from sage_ini.model.behaviors import CastleBehavior
from sage_ini.model.state import build_variations, find_body, has_kindof, select_command_set
from sage_utils.views import (
    _safe,
    build_cost_view,
    command_set_buttons,
    display_name,
    faction_for_side,
    localize,
    recruited_hero_names,
)
from sage_utils.views import description as object_description

# Command action names (matched on the resolved CommandTypes enum's .name). A structure is built by
# FOUNDATION_CONSTRUCT (on a base plot), DOZER_CONSTRUCT (worker-built), UNIT_BUILD, or
# CASTLE_UNPACK_EXPLICIT_OBJECT (an economy/expansion plot dropping a specific building); a unit is
# trained by UNIT_BUILD. The button's `Object` is the built/trained object either way — KindOf
# decides which it is.
_REVIVE = "REVIVE"
_BUILD_COMMANDS = frozenset(
    {"UNIT_BUILD", "FOUNDATION_CONSTRUCT", "DOZER_CONSTRUCT", "CASTLE_UNPACK_EXPLICIT_OBJECT"}
)
_UPGRADE_COMMANDS = frozenset({"OBJECT_UPGRADE", "PLAYER_UPGRADE", "PURCHASE_SCIENCE"})

# The plot flags whose buildings and bases are gathered, named explicitly. Scanning every object
# with a CastleBehavior pulls in dozens of noisy variants — castle orientations (…NW/…NE),
# prebuilt/AI/map-template flags, even other factions' captured flags — that all carry
# CastleToUnpackForFaction rows. Only these are wanted: the castle base, the camp base, the economy
# plot, and the expansion (outpost) plot.
_START_FLAGS = (
    "FestungPlotFlag_Real",
    "LagerPlotFlag_Real",
    "WirtschaftPlotFlag_Real",
    "ExpansionPlotFlag",
)

# Start-flag classification by name token (German + English), since the flag carries no kind flag.
_FLAG_KIND_TOKENS: tuple[tuple[StartPointKind, tuple[str, ...]], ...] = (
    (StartPointKind.SETTLEMENT, ("siedlung", "settlement")),
    (StartPointKind.ECONOMY, ("wirtschaft", "economy")),
    (StartPointKind.OUTPOST, ("aussenposten", "outpost", "vorposten", "expansion")),
    (StartPointKind.CAMP, ("lager", "camp")),
    (StartPointKind.CASTLE, ("festung", "castle", "burg", "veste")),
)


def _faction_side(faction) -> str | None:
    raw = faction._fields.get("Side")
    if raw is None:
        return None
    return str(raw[-1] if isinstance(raw, list) else raw)


def _faction_upgrades(side: str | None) -> set[str]:
    """The upgrade(s) that identify a faction to the engine, by Edain's `Upgrade_<Side>Faction`
    convention (e.g. `Upgrade_MenFaction`). A shared object — an economy/expansion plot, a build
    foundation — swaps to the faction's palette through a `CommandSetUpgrade` triggered by this, so
    resolving its command set under these upgrades yields the faction-specific buttons. Harmless
    when the upgrade isn't used; it simply activates nothing."""
    return {f"Upgrade_{side}Faction"} if side else set()


def _object_side(game, name: str | None) -> str | None:
    """The `Side` token of a structure, walking the parent chain — used to keep a faction's own
    start points and drop the cross-faction structures that neutral/captured flags also unpack."""
    obj = game.objects.get(name) if name else None
    while obj is not None:
        raw = obj._fields.get("Side")
        if raw is not None:
            return str(raw[-1] if isinstance(raw, list) else raw).split()[0]
        obj = getattr(obj, "parent", None)
    return None


def _field_token(obj, field: str) -> str | None:
    raw = obj._fields.get(field)
    if raw is None:
        return None
    return str(raw[-1] if isinstance(raw, list) else raw).split()[0]


def _build_variation(game, obj):
    """The build variation `obj` resolves to, or None. A constructable building can be a build shell
    (no Body of its own, only a `BuildVariations` list); its real command set, body and production
    live on a variation object. Returns the first loaded variation when `obj` is such a shell, so
    the walk reads the building's actual buttons rather than the shell's placeholder set."""
    if find_body(obj) is not None:
        return None
    for name in build_variations(obj):
        variation = game.objects.get(name)
        if variation is not None:
            return variation
    return None


def _describe(game, obj) -> str:
    """An object's localized Description (or RecruitText fallback) for its page, with the string
    table's literal `\\n` line breaks turned into real newlines so the UI can lay them out."""
    text = object_description(game, obj)
    return text.replace("\\n", "\n") if text else ""


def _classify_flag(flag_name: str) -> StartPointKind:
    lowered = flag_name.casefold()
    for kind, tokens in _FLAG_KIND_TOKENS:
        if any(token in lowered for token in tokens):
            return kind
    return StartPointKind.CASTLE


def _macro_number(game, token: str) -> float | None:
    resolved = game.get_macro(token) if game is not None else token
    try:
        return float(resolved)
    except (TypeError, ValueError):
        return None


def _unpack_rows(game, module) -> list[tuple[str, str, float | None]]:
    """`(side, base_or_structure_name, cost)` for each `CastleToUnpackForFaction` line, the base
    name macro-resolved (`gondor_castle` is a base-layout name, not an ini object, so it is kept
    raw; a macro that resolves to a real name is expanded)."""
    rows: list[tuple[str, str, float | None]] = []
    raw = module._fields.get("CastleToUnpackForFaction")
    if raw is None:
        return rows
    for entry in raw if isinstance(raw, list) else [raw]:
        tokens = str(entry).split()
        if len(tokens) < 2:
            continue
        side, target = tokens[0], str(game.get_macro(tokens[1])).split()[0]
        cost = _macro_number(game, tokens[2]) if len(tokens) > 2 else None
        rows.append((side, target, cost))
    return rows


def _start_points(game, side: str, bases_dir: Path | None, start_flags) -> list[StartPoint]:
    """The `start_flags` that unpack something for `side`, with each base layout decomposed. Only
    the named flags are consulted (not every CastleBehavior in the game)."""
    points: list[StartPoint] = []
    for flag_name in start_flags:
        flag = game.objects.get(flag_name)
        if flag is None:
            continue
        castle = next(
            (m for m in getattr(flag, "modules", ()) if isinstance(m, CastleBehavior)), None
        )
        if castle is None:
            continue
        for row_side, target, cost in _unpack_rows(game, castle):
            if row_side != side:
                continue
            kind = _classify_flag(flag.name)
            point = StartPoint(flag=flag.name, kind=kind, cost=cost)
            target_obj = game.objects.get(target)
            if target_obj is not None and has_kindof(target_obj, "STRUCTURE"):
                # The flag drops a single, named structure (settlement / single-structure outpost).
                point.structure = target
            else:
                # The flag names a base *layout*; decompose it into its placed structures.
                point.base = target
                layout = resolve_base_layout(game, bases_dir, target)
                point.citadel = layout.citadel
                point.foundations = layout.foundations
                point.prebuilt = layout.prebuilt
            # Neutral/captured flags list every faction's unpack target; keep only the start points
            # whose own structure belongs to this faction. An unverifiable base (no parsed citadel)
            # is kept — it simply contributes no seeds.
            owned_side = _object_side(game, point.structure or point.citadel)
            if owned_side is not None and owned_side != side:
                continue
            points.append(point)
    return points


def _power_from_button(game, obj, button) -> Power | None:
    """A SPELL_BOOK / SPECIAL_POWER button resolved to a `Power` (its created objects, transform,
    weapon, modifiers — see `resolve_power`). None when the button names no power."""
    power = _safe(lambda: button.SpecialPower)
    name = getattr(power, "name", None)
    if not name:
        return None
    display = display_name(game, power) or localize(game, _safe(lambda: button.TextLabel)) or name
    effect = localize(game, _safe(lambda: button.DescriptLabel)) or ""
    return resolve_power(game, obj, name, display=display, effect=effect)


def _is_ability(command: str | None) -> bool:
    return command == "SPELL_BOOK" or (command is not None and command.startswith("SPECIAL_POWER"))


def _spellbook(game, faction, faction_upgrades: set[str]) -> Spellbook | None:
    name = _field_token(faction, "SpellBookMp") or _field_token(faction, "SpellBook")
    if not name:
        return None
    book = Spellbook(name=name)
    obj = game.objects.get(name)
    if obj is None:
        return book
    command_set = select_command_set(obj, faction_upgrades)
    if command_set is None:
        return book
    seen: set[str] = set()
    for _slot, _button_name, button in command_set_buttons(game, command_set):
        command = getattr(_safe(lambda b=button: b.Command), "name", None)
        if not _is_ability(command):
            continue
        power = _power_from_button(game, obj, button)
        if power is not None and power.name not in seen:
            seen.add(power.name)
            book.powers.append(power)
    return book


class _Builder:
    """Accumulates the faction-level leaf indexes while the structure walk runs, so a unit/hero/
    upgrade reachable from several buildings is stored once, with one `Producer` edge per
    building."""

    def __init__(self, game, faction, faction_upgrades: set[str]):
        self.game = game
        self.faction = faction
        self.faction_upgrades = faction_upgrades
        self.structures: dict[str, Structure] = {}
        self.units: dict[str, ProducedUnit] = {}
        self.heroes: dict[str, RecruitedHero] = {}
        self.upgrades: dict[str, ResearchableUpgrade] = {}

    def _display(self, obj) -> str:
        return display_name(self.game, obj) or obj.name

    def _add_unit(self, target, producer: Producer) -> None:
        unit = self.units.get(target.name)
        if unit is None:
            cost = build_cost_view(target)
            unit = ProducedUnit(
                name=target.name,
                display=self._display(target),
                description=_describe(self.game, target),
                cost=cost["BuildCost"],
                command_points=cost["CommandPoints"],
                profile=build_profile(self.game, target, self.faction_upgrades),
            )
            self.units[target.name] = unit
        unit.producers.append(producer)

    def _add_hero(self, hero, producer: Producer) -> None:
        record = self.heroes.get(hero.name)
        if record is None:
            record = RecruitedHero(
                name=hero.name,
                display=self._display(hero),
                description=_describe(self.game, hero),
                profile=build_profile(self.game, hero, self.faction_upgrades),
            )
            self.heroes[hero.name] = record
        record.producers.append(producer)

    def _add_upgrade(self, upgrade, producer: Producer) -> None:
        record = self.upgrades.get(upgrade.name)
        if record is None:
            record = ResearchableUpgrade(
                name=upgrade.name,
                display=display_name(self.game, upgrade) or upgrade.name,
                description=_describe(self.game, upgrade),
                cost=_safe(lambda: upgrade.BuildCost),
            )
            self.upgrades[upgrade.name] = record
        record.producers.append(producer)

    def walk(self, seeds: dict[str, StructureRole]) -> None:
        """Breadth-first over the seed structures; `UNIT_BUILD` structure targets extend the walk
        as foundation buildings. `seeds` maps a structure name to its role; discovered structures
        default to FOUNDATION_BUILDING."""
        queue: list[tuple[str, StructureRole]] = list(seeds.items())
        while queue:
            name, role = queue.pop(0)
            if name in self.structures:
                continue
            obj = self.game.objects.get(name)
            if obj is None:
                continue
            # Resolve the building's own stats from its body-bearing object (the variation, if it is
            # a build shell), so a shell's health/weapons aren't read as empty.
            stats_obj = _build_variation(self.game, obj) or obj
            structure = Structure(
                name=name,
                display=self._display(obj),
                role=role,
                description=_describe(self.game, obj),
                profile=build_profile(self.game, stats_obj, self.faction_upgrades),
            )
            self.structures[name] = structure
            self._resolve_structure(obj, structure, queue)

    def _resolve_structure(self, obj, structure: Structure, queue: list) -> None:
        # A constructable building can be a build shell (no Body, only `BuildVariations`); its real
        # command set, body and production live on the variation, so resolve from there.
        variation = _build_variation(self.game, obj)
        source = variation if variation is not None else obj
        if variation is not None:
            structure.variation = variation.name
        # Resolve under the faction's identifying upgrades so a shared plot/foundation shows the
        # faction's palette (its CommandSetUpgrade-swapped buttons), not the generic default.
        command_set = select_command_set(source, self.faction_upgrades)
        if command_set is not None:
            for _slot, button_name, button in command_set_buttons(self.game, command_set):
                self._resolve_button(source, structure, button_name, button, queue)
        for hero_name in recruited_hero_names(self.game, source):
            hero = self.game.objects.get(hero_name)
            if hero is None:
                continue
            structure.recruits_heroes.append(hero_name)
            self._add_hero(hero, Producer(structure=structure.name, button=_REVIVE))

    def _resolve_button(self, obj, structure: Structure, button_name, button, queue) -> None:
        command = getattr(_safe(lambda: button.Command), "name", None)
        shortcut = _shortcut(self.game, button)
        if command in _BUILD_COMMANDS:
            target = _safe(lambda: button.Object)
            if target is None:
                return
            producer = Producer(structure.name, button_name, shortcut)
            if has_kindof(target, "STRUCTURE"):
                queue.append((target.name, StructureRole.FOUNDATION_BUILDING))
            else:
                structure.trains_units.append(target.name)
                self._add_unit(target, producer)
        elif command in _UPGRADE_COMMANDS:
            upgrade = _safe(lambda: button.Upgrade)
            if upgrade is not None:
                structure.researches_upgrades.append(upgrade.name)
                self._add_upgrade(upgrade, Producer(structure.name, button_name, shortcut))
        elif _is_ability(command):
            power = _power_from_button(self.game, obj, button)
            if power is not None:
                structure.abilities.append(power)


def _shortcut(game, button) -> str:
    """The localized hotkey suffix on a button's label (e.g. the trailing "(&Q)"), or "" — kept so
    a producer edge can show the key the player presses."""
    label = localize(game, _safe(lambda: button.TextLabel)) or ""
    marker = label.rfind("(&")
    return label[marker:].strip() if marker != -1 else ""


def build_faction_graph(
    game, faction, bases_dir: Path | None = None, start_flags=_START_FLAGS
) -> FactionGraph:
    """The full ownership graph for one `PlayerTemplate`. `bases_dir` (the mod's `bases/` folder)
    enables base-layout decomposition; without it start points record only the base name.
    `start_flags` are the plot-flag object names whose buildings/bases are gathered (defaults to the
    three canonical Edain plots — castle, economy, expansion)."""
    side = _faction_side(faction)
    faction_upgrades = _faction_upgrades(side)
    graph = FactionGraph(
        name=faction.name,
        display=display_name(game, faction) or faction.name,
        side=side,
        spellbook=_spellbook(game, faction, faction_upgrades),
    )
    if side is not None:
        graph.start_points = _start_points(game, side, bases_dir, start_flags)

    seeds: dict[str, StructureRole] = {}
    for point in graph.start_points:
        # A plot flag that is itself a build plot (an economy/expansion BASE_FOUNDATION) is walked
        # too — its faction command set drops the explicit economy/outpost buildings.
        flag = game.objects.get(point.flag)
        if flag is not None and has_kindof(flag, "BASE_FOUNDATION"):
            seeds.setdefault(point.flag, StructureRole.FOUNDATION)
        if point.citadel:
            seeds.setdefault(point.citadel, StructureRole.CITADEL)
        for foundation in point.foundations:
            seeds.setdefault(foundation, StructureRole.FOUNDATION)
        for prebuilt in point.prebuilt:
            seeds.setdefault(prebuilt, StructureRole.PREBUILT)
        if point.structure:
            seeds.setdefault(point.structure, StructureRole.STANDALONE)

    builder = _Builder(game, faction, faction_upgrades)
    builder.walk(seeds)
    graph.structures = builder.structures
    graph.units = builder.units
    graph.heroes = builder.heroes
    graph.upgrades = builder.upgrades
    graph.created = _collect_created(game, graph, faction_upgrades)
    return graph


# A guard on the created-object expansion: a summon chain can fan out (eggs hatch units that summon
# more), so cap how many created objects one graph materialises.
_MAX_CREATED = 400


def _iter_powers(graph: FactionGraph):
    """Every resolved power in the graph — spellbook, structure abilities, and unit/hero
    abilities — so their created/transform targets can be gathered."""
    if graph.spellbook is not None:
        yield from graph.spellbook.powers
    for structure in graph.structures.values():
        yield from structure.abilities
    for unit in graph.units.values():
        if unit.profile is not None:
            yield from unit.profile.abilities
    for hero in graph.heroes.values():
        if hero.profile is not None:
            yield from hero.profile.abilities


def _collect_created(game, graph: FactionGraph, faction_upgrades: set[str]) -> dict:
    """Materialise the objects a power creates or turns into, but that nothing builds/recruits, as
    navigable `CreatedObject` nodes with their own stat profile. Expands transitively (a summon's
    own abilities may create more) to a cap, so links from a power resolve to a real page."""
    known = set(graph.units) | set(graph.heroes) | set(graph.structures)
    created: dict[str, CreatedObject] = {}
    pending: list[str] = []

    def enqueue(power: Power) -> None:
        for name, _display in (*power.creates, *power.transforms_into):
            if name not in known and name not in created:
                pending.append(name)

    for power in _iter_powers(graph):
        enqueue(power)
    while pending and len(created) < _MAX_CREATED:
        name = pending.pop()
        if name in created or name in known:
            continue
        obj = game.objects.get(name)
        if obj is None:
            continue
        profile = build_profile(game, obj, faction_upgrades)
        created[name] = CreatedObject(
            name=name,
            display=display_name(game, obj) or name,
            description=_describe(game, obj),
            profile=profile,
        )
        for power in profile.abilities:  # a created object's abilities may create more
            enqueue(power)
    return created


def playable_factions(game) -> list:
    """The playable `PlayerTemplate`s (a faction with `PlayableSide`), in faction-table order."""
    return [f for f in game.factions.values() if _safe(lambda f=f: f.PlayableSide)]


def build_faction_graphs(game, bases_dir: Path | None = None) -> list[FactionGraph]:
    """A graph for every playable faction, in faction-table order — what the CLI builds when no
    single faction is named."""
    return [build_faction_graph(game, faction, bases_dir) for faction in playable_factions(game)]


def find_faction(game, name: str):
    """A playable faction by template name (exact) or `Side` token (e.g. "Gondor"), or None."""
    direct = game.factions.get(name)
    if direct is not None and _safe(lambda: direct.PlayableSide):
        return direct
    for faction in playable_factions(game):
        if _faction_side(faction) == name:
            return faction
    return faction_for_side(game, name)
