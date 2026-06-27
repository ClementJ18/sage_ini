"""The faction ownership graph — the explicit link between a faction and every object a player
of it can see and interact with.

These are plain dataclasses, deliberately serializable (`to_dict`), forming an owner -> owned
tree. Every leaf records *why* the faction owns it (the producing structure and the source
command button), so the link is explicit rather than implied. The graph is assembled by
`sage_edain.graph.build_faction_graph` from a loaded `Game`; nothing here touches the model
directly, so the shapes stay easy to inspect, diff and emit as JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class StartPointKind(StrEnum):
    """How a faction's starting plot flag deploys. A castle or camp unpacks a whole base
    (citadel + foundations); an outpost or economy plot is itself a build plot that may also unpack
    a small base; a settlement unpacks a single structure."""

    CASTLE = "castle"
    CAMP = "camp"
    OUTPOST = "outpost"
    ECONOMY = "economy"
    SETTLEMENT = "settlement"


class StructureRole(StrEnum):
    """A structure's place in the base. The citadel is the unpacked keep; a foundation building
    is something constructed on a base plot; a prebuilt structure ships with the base; an
    expansion is built from an outpost/settlement plot."""

    CITADEL = "citadel"
    FOUNDATION = "foundation"
    FOUNDATION_BUILDING = "foundation_building"
    PREBUILT = "prebuilt"
    STANDALONE = "standalone"


@dataclass
class Producer:
    """One edge into a leaf: the structure that produces it and the command button that does so.
    A unit/hero/upgrade reachable from several buildings carries one `Producer` per building."""

    structure: str  # the producing structure's object name
    button: str  # the command button's name
    shortcut: str = ""  # the localized hotkey label, when the button has one


@dataclass
class ProducedUnit:
    """A unit a structure trains (a `UNIT_BUILD` button's target object). `description` is the
    object's localized Description (or RecruitText)."""

    name: str
    display: str
    description: str = ""
    cost: float | None = None
    command_points: float | None = None
    profile: Profile | None = None
    producers: list[Producer] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display": self.display,
            "description": self.description,
            "cost": self.cost,
            "command_points": self.command_points,
            "profile": self.profile.to_dict() if self.profile else None,
            "producers": [vars(p) for p in self.producers],
        }


@dataclass
class RecruitedHero:
    """A hero a structure recruits — resolved by the index-based REVIVE logic (a faction's
    buildable-hero order mapped onto a building's revive slots)."""

    name: str
    display: str
    description: str = ""
    profile: Profile | None = None
    producers: list[Producer] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display": self.display,
            "description": self.description,
            "profile": self.profile.to_dict() if self.profile else None,
            "producers": [vars(p) for p in self.producers],
        }


@dataclass
class ResearchableUpgrade:
    """An upgrade/science a structure researches (an `OBJECT_UPGRADE`/`PLAYER_UPGRADE`/
    `PURCHASE_SCIENCE` button)."""

    name: str
    display: str
    description: str = ""
    cost: float | None = None
    producers: list[Producer] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display": self.display,
            "description": self.description,
            "cost": self.cost,
            "producers": [vars(p) for p in self.producers],
        }


@dataclass
class Power:
    """A spellbook power or a unit/hero ability (a SPELL_BOOK / SPECIAL_POWER button), with its
    resolved effect. `kind` is the primary classification (summon / transform / weapon / modifier /
    "" when only a description is known). The effect links: `creates` the objects it summons,
    `transforms_into` the form(s) it turns the user into (each an `(object name, display)` pair),
    `weapon` a special weapon it fires, and `modifiers` the (stat, amount) buffs it grants. `effect`
    is the in-game description; `cooldown` the recharge time in seconds."""

    name: str
    display: str
    kind: str = ""
    cooldown: float | None = None
    effect: str = ""
    creates: list[tuple[str, str]] = field(default_factory=list)  # (object name, display)
    transforms_into: list[tuple[str, str]] = field(default_factory=list)  # (object name, display)
    weapon: Weapon | None = None
    modifiers: list[tuple[str, str]] = field(default_factory=list)  # (stat label, amount)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display": self.display,
            "kind": self.kind,
            "cooldown": self.cooldown,
            "effect": self.effect,
            "creates": [{"name": n, "display": d} for n, d in self.creates],
            "transforms_into": [{"name": n, "display": d} for n, d in self.transforms_into],
            "weapon": self.weapon.to_dict() if self.weapon else None,
            "modifiers": [{"stat": s, "amount": a} for s, a in self.modifiers],
        }


@dataclass
class Weapon:
    """One of an object's weapons, summarised for a non-technical reader: whether it is a melee or
    ranged attack, its reach, per-hit damage and damage type, and sustained damage-per-second."""

    kind: str  # "melee" | "ranged"
    damage: float | None = None
    damage_type: str | None = None
    range: float | None = None
    dps: float | None = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "damage": self.damage,
            "damage_type": self.damage_type,
            "range": self.range,
            "dps": self.dps,
        }


@dataclass
class Profile:
    """A read-only stat snapshot of an object, mirroring sage_ui's UnitPanel as plain data: the
    headline stats, its weapons, how much damage of each type it survives (`defenses`), and its
    abilities. Resolved at base state (no upgrades, lowest rank); for a horde the combat stats come
    from the contained unit and the cost from the horde."""

    health: float | None = None
    speed: float | None = None
    vision: float | None = None
    build_cost: float | None = None
    build_time: float | None = None
    command_points: float | None = None
    weapons: list[Weapon] = field(default_factory=list)
    defenses: list[tuple[str, float]] = field(default_factory=list)  # (damage type, effective HP)
    abilities: list[Power] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "health": self.health,
            "speed": self.speed,
            "vision": self.vision,
            "build_cost": self.build_cost,
            "build_time": self.build_time,
            "command_points": self.command_points,
            "weapons": [w.to_dict() for w in self.weapons],
            "defenses": [{"damage_type": t, "effective_health": hp} for t, hp in self.defenses],
            "abilities": [a.to_dict() for a in self.abilities],
        }


@dataclass
class Structure:
    """A structure the faction can field, with what it produces. Listed once per object; its
    producers are reachable from the leaf nodes' `Producer` edges."""

    name: str
    display: str
    role: StructureRole
    description: str = ""
    variation: str | None = None  # the BuildVariations object its real command set/body came from
    profile: Profile | None = None
    trains_units: list[str] = field(default_factory=list)  # ProducedUnit names
    recruits_heroes: list[str] = field(default_factory=list)  # RecruitedHero names
    researches_upgrades: list[str] = field(default_factory=list)  # ResearchableUpgrade names
    abilities: list[Power] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display": self.display,
            "role": self.role.value,
            "description": self.description,
            "variation": self.variation,
            "profile": self.profile.to_dict() if self.profile else None,
            "trains_units": self.trains_units,
            "recruits_heroes": self.recruits_heroes,
            "researches_upgrades": self.researches_upgrades,
            "abilities": [a.to_dict() for a in self.abilities],
        }


@dataclass
class StartPoint:
    """A starting plot flag the faction can place, and what it deploys. `base` names the base
    layout (a `.bse` under the mod's `bases/`) a castle/camp/outpost unpacks; `structure` names the
    single structure a settlement (or single-structure outpost) drops instead. When the base layout
    is parsed (needs sagemap), `citadel`, `foundations` and `prebuilt` are filled with the object
    templates placed in it, classified by KindOf."""

    flag: str
    kind: StartPointKind
    base: str | None = None
    structure: str | None = None
    cost: float | None = None
    citadel: str | None = None
    foundations: list[str] = field(default_factory=list)
    prebuilt: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "flag": self.flag,
            "kind": self.kind.value,
            "base": self.base,
            "structure": self.structure,
            "cost": self.cost,
            "citadel": self.citadel,
            "foundations": self.foundations,
            "prebuilt": self.prebuilt,
        }


@dataclass
class CreatedObject:
    """An object that exists only because a power makes it — a summoned creature, a transform form —
    rather than something built or recruited. Carries the same stat `profile` as any unit so it gets
    its own navigable detail page when a power's `creates`/`transforms_into` links to it."""

    name: str
    display: str
    description: str = ""
    profile: Profile | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display": self.display,
            "description": self.description,
            "profile": self.profile.to_dict() if self.profile else None,
        }


@dataclass
class Spellbook:
    """The faction's spellbook object and the powers its command set exposes."""

    name: str
    powers: list[Power] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "powers": [p.to_dict() for p in self.powers]}


@dataclass
class FactionGraph:
    """The whole explicit ownership link for one faction. The `start_points` deploy bases whose
    `structures` produce the `units`, `heroes` and `upgrades` — each leaf de-duplicated and
    carrying its `Producer` edges back to the buildings that yield it."""

    name: str
    display: str
    side: str | None
    spellbook: Spellbook | None = None
    start_points: list[StartPoint] = field(default_factory=list)
    structures: dict[str, Structure] = field(default_factory=dict)
    units: dict[str, ProducedUnit] = field(default_factory=dict)
    heroes: dict[str, RecruitedHero] = field(default_factory=dict)
    upgrades: dict[str, ResearchableUpgrade] = field(default_factory=dict)
    created: dict[str, CreatedObject] = field(default_factory=dict)  # power-created objects/forms

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display": self.display,
            "side": self.side,
            "spellbook": self.spellbook.to_dict() if self.spellbook else None,
            "start_points": [s.to_dict() for s in self.start_points],
            "structures": {k: v.to_dict() for k, v in self.structures.items()},
            "units": {k: v.to_dict() for k, v in self.units.items()},
            "heroes": {k: v.to_dict() for k, v in self.heroes.items()},
            "upgrades": {k: v.to_dict() for k, v in self.upgrades.items()},
            "created": {k: v.to_dict() for k, v in self.created.items()},
        }
