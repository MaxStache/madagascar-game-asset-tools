import sys
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, BinaryIO, TypeVar, override

from tfbscript.ansi import builtin, keyword, variable, variable_global
from tfbscript.binary import write_u32
from tfbscript.string_table import StringTable, StringTableEntry

if TYPE_CHECKING:
    from tfbscript.binary import BinaryReader
    from tfbscript.opcodes.base import Opcode, ParserContext

_OpcodeT = TypeVar("_OpcodeT", bound="Opcode")

LOCAL_BASE = 0x3FC0D
BUILTIN_BASE = 0x3FFFA
NULL_REF = 0xFFFFFFFF

# References whose type resolution is in progress, to break cyclic
# builtin producer chains (see get_resolved_type).
_RESOLVING: set[int] = set()

# Fields `raw` is composed from: assigning any of them re-runs update_raw.
_RAW_INPUTS = frozenset(
    {"index", "member", "scope", "sub", "kind", "builtin_kind", "slot"}
)


# fmt: off
class ReferenceType(Enum):
    LOCAL   = 0
    GLOBAL  = 1
    BUILTIN = 2
    NULL    = 3

class BuiltinType(Enum):
    SELF           = 0x3FFFF
    CONTROLLED     = 0x3FFFE
    EACH           = 0x3FFFD # current in for each
    SUBSET         = 0x3FFFC # filtered list of any kind
    MESSAGE_VALUE  = 0x3FFFB
    FOUND_VARIABLE = 0x3FFFA

BUILTIN_LABELS = {                                          # type resolving implemented
    BuiltinType.SELF          : "my",                     # yes
    BuiltinType.CONTROLLED    : "[~controlled]",            # yes
    BuiltinType.EACH          : "[~current in for each]",   # no (see comment)
    BuiltinType.SUBSET        : "[~subset]",                # yes
    BuiltinType.MESSAGE_VALUE : "[~message value]",         # yes
    BuiltinType.FOUND_VARIABLE: "[~found variable]",        # yes
}
# fmt: on

BINDINGS = {
    "actor": {
        0x01: {"name": "health", "type": "value"},
        0x02: {"name": "waypoints", "type": "set", "of": "waypoint"},
        0x03: {"name": "origin", "type": "value"},
        0x04: {"name": "destination (point)", "type": "value"},
        0x05: {"name": "heading (OBSOLETE)", "type": "value"},
        0x06: {"name": "facing (OBSOLETE)", "type": "value"},
        0x07: {"name": "current speed", "type": "value"},
        0x08: {"name": "altitude", "type": "value"},
        0x09: {"name": "attach points", "type": "set", "of": "attachment"},
        0x0A: {"name": "activation range fade percent", "type": "value"},
        0x0B: {"name": "activation range", "type": "value"},
        0x0C: {"name": "deactivation range", "type": "value"},
        0x0D: {"name": "clones", "type": "set", "of": "actor"},
        0x0E: {"name": "ground top speed", "type": "value"},
        0x0F: {"name": "ground turn rate", "type": "value"},
        0x10: {"name": "ground acceleration", "type": "value"},
        0x11: {"name": "ground deceleration", "type": "value"},
        0x12: {"name": "move type", "type": "value"},
        0x13: {"name": "air top speed", "type": "value"},
        0x14: {"name": "air turn rate", "type": "value"},
        0x15: {"name": "air acceleration", "type": "value"},
        0x16: {"name": "air deceleration", "type": "value"},
        0x17: {"name": "jump delay", "type": "value"},
        0x18: {"name": "initial jump velocity", "type": "value"},
        0x19: {"name": "jump coast frames", "type": "value"},
        0x1A: {"name": "up top speed", "type": "value"},
        0x1B: {"name": "up acceleration", "type": "value"},
        0x1C: {"name": "down top speed", "type": "value"},
        0x1D: {"name": "down acceleration", "type": "value"},
        0x1E: {"name": "animation rate multiplier", "type": "value"},
        0x1F: {"name": "weight", "type": "value"},
        0x20: {"name": "bounce restitution", "type": "value"},
        0x21: {"name": "X offset", "type": "value"},  # Extend box X
        0x22: {"name": "Y offset", "type": "value"},  # Extend box Y
        0x23: {"name": "Z offset", "type": "value"},  # Extend box Z
        0x24: {"name": "W extend", "type": "value"},  # Extend box W extend
        0x25: {"name": "L extend", "type": "value"},  # Extend box L extend
        0x26: {"name": "H extend", "type": "value"},  # Extend box H extend
        0x27: {"name": "cone angle", "type": "value"},
        0x28: {"name": "cone length", "type": "value"},
        0x29: {"name": "cone sweep offset", "type": "value"},
        0x2A: {"name": "blip color", "type": "value", "of": "color"},
        0x2B: {"name": "cone color", "type": "value", "of": "color"},
        0x2C: {"name": "solid collision", "type": "value"},
        0x2D: {"name": "wall collision", "type": "value"},
        0x2E: {"name": "visible on radar", "type": "value"},
        0x2F: {"name": "wall climber", "type": "value"},
        0x30: {"name": "cut-scene ignore", "type": "value"},
        0x31: {"name": "ignore ground color", "type": "value"},
        0x32: {"name": "tilts with ground", "type": "value"},
        0x33: {"name": "no shadow", "type": "value"},
        0x34: {"name": "ID", "type": "value"},
        0x35: {"name": "mesh collider", "type": "value"},
        0x36: {"name": "triangles collide", "type": "value"},
        0x37: {"name": "tint color", "type": "value", "of": "color"},
        0x38: {"name": "turrets", "type": "set", "of": "turret"},
    },
    "camera": {
        0x01: {"name": "look from", "type": "value"},
        0x02: {"name": "look from horizontal offset", "type": "value"},
        0x03: {"name": "look from vertical offset", "type": "value"},
        0x04: {"name": "look from heading offset", "type": "value"},
        0x05: {"name": "look from heading relative", "type": "value"},
        0x06: {"name": "look at", "type": "value"},
        0x07: {"name": "look at horizontal offset", "type": "value"},
        0x08: {"name": "look at vertical offset", "type": "value"},
        0x09: {"name": "look at heading offset", "type": "value"},
        0x0A: {"name": "look at heading relative", "type": "value"},
        0x0B: {"name": "field of view", "type": "value"},
        0x0C: {"name": "laziness", "type": "value"},
        0x0D: {"name": "percent complete", "type": "value"},
        0x0E: {"name": "time remaining", "type": "value"},
        0x0F: {"name": "Vertical Follow At", "type": "value"},
        0x10: {"name": "Horizontal Follow", "type": "value"},
        0x11: {"name": "Current Facing", "type": "value"},
        0x12: {"name": "Vertical Follow From", "type": "value"},
        0x13: {"name": "pitch control", "type": "value"},
        0x14: {"name": "roll", "type": "value"},
    },
    "sprite": {  # TODO: confirm labels
        0x01: {"name": "content", "type": "value"},
        0x02: {"name": "location", "type": "value", "of": "2D"},
        0x03: {"name": "scale", "type": "value", "of": "2D"},
        0x04: {"name": "rotation", "type": "value"},
        0x05: {"name": "tint color", "type": "value", "of": "color"},
        0x06: {"name": "justification", "type": "value"},
        0x07: {"name": "visible", "type": "value"},
        0x08: {"name": "clones", "type": "set", "of": "sprite"},
        0x09: {"name": "priority", "type": "value"},  # z-order!?
        0x0A: {"name": "pixel extends", "type": "value", "of": "2D"},
    },
    "sound": {
        0x01: {"name": "volume", "type": "value"},
        0x02: {"name": "pitch", "type": "value"},
        0x03: {"name": "elapsed time", "type": "value"},
        0x04: {"name": "remaining time", "type": "value"},
    },
    "2D": {
        0x01: {"name": "x", "type": "value"},
        0x02: {"name": "y", "type": "value"},
    },
    "color": {
        0x01: {"name": "r", "type": "value"},
        0x02: {"name": "g", "type": "value"},
        0x03: {"name": "b", "type": "value"},
        0x04: {"name": "a", "type": "value"},
    },
    "controller": {
        0x01: {"name": "circle button", "type": "value"},
        0x02: {"name": "triangle button", "type": "value"},
        0x03: {"name": "X button", "type": "value"},
        0x04: {"name": "square button", "type": "value"},
        0x05: {"name": "select button", "type": "value"},
        0x06: {"name": "start button", "type": "value"},
        0x07: {"name": "L1 button", "type": "value"},
        0x08: {"name": "R1 button", "type": "value"},
        0x09: {"name": "L2 button", "type": "value"},
        0x0A: {"name": "R2 button", "type": "value"},
        0x0B: {"name": "DPad left", "type": "value"},
        0x0C: {"name": "DPad right", "type": "value"},
        0x0D: {"name": "DPad up", "type": "value"},
        0x0E: {"name": "DPad down", "type": "value"},
        0x0F: {"name": "analog1 left", "type": "value"},
        0x10: {"name": "analog1 right", "type": "value"},
        0x11: {"name": "analog1 up", "type": "value"},
        0x12: {"name": "analog1 down", "type": "value"},
        0x13: {"name": "analog2 left", "type": "value"},
        0x14: {"name": "analog2 right", "type": "value"},
        0x15: {"name": "analog2 up", "type": "value"},
        0x16: {"name": "analog2 down", "type": "value"},
        0x17: {"name": "analog1 heading", "type": "value"},
        0x18: {"name": "analog1 magnitude", "type": "value"},
        0x19: {"name": "analog2 heading", "type": "value"},
        0x1A: {"name": "analog2 magnitude", "type": "value"},
        0x1B: {"name": "connection", "type": "value"},
    },
    "MOTION BLUR": {
        0x01: {"name": "amount", "type": "value"},
        0x02: {"name": "offset-x", "type": "value"},
        0x03: {"name": "offset-y", "type": "value"},
        0x04: {"name": "scale x-axis", "type": "value"},
        0x05: {"name": "scale y-axis", "type": "value"},
        0x06: {"name": "scale", "type": "value"},
        0x07: {"name": "angle", "type": "value"},
    },
    "animation mapping": {
        0x01: {"name": "ambient", "type": "value"},
        0x02: {"name": "slowest move", "type": "value"},
        0x03: {"name": "slow move", "type": "value"},
        0x04: {"name": "fast move", "type": "value"},
        0x05: {"name": "jump", "type": "value"},
        0x06: {"name": "fall", "type": "value"},
        0x07: {"name": "youch", "type": "value"},
        0x08: {"name": "slide", "type": "value"},
        0x09: {"name": "attack 1", "type": "value"},
        0x0A: {"name": "attack 2", "type": "value"},
        0x0B: {"name": "tumble", "type": "value"},
        0x0C: {"name": "extra 1", "type": "value"},
        0x0D: {"name": "extra 2", "type": "value"},
        0x0E: {"name": "extra 3", "type": "value"},
        0x0F: {"name": "extra 4", "type": "value"},
        0x10: {"name": "extra 5", "type": "value"},
        0x11: {"name": "extra 6", "type": "value"},
        0x12: {"name": "extra 7", "type": "value"},
        0x13: {"name": "extra 8", "type": "value"},
        0x14: {"name": "extra 9", "type": "value"},
        0x15: {"name": "extra 10", "type": "value"},
        0x16: {"name": "extra 11", "type": "value"},
        0x17: {"name": "extra 12", "type": "value"},
        0x18: {"name": "extra 13", "type": "value"},
        0x19: {"name": "extra 14", "type": "value"},
        0x1A: {"name": "extra 15", "type": "value"},
        0x1B: {"name": "extra 16", "type": "value"},
        0x1C: {"name": "extra 17", "type": "value"},
        0x1D: {"name": "extra 18", "type": "value"},
        0x1E: {"name": "extra 19", "type": "value"},
        0x1F: {"name": "extra 20", "type": "value"},
        0x20: {"name": "extra 21", "type": "value"},
        0x21: {"name": "extra 22", "type": "value"},
        0x22: {"name": "extra 23", "type": "value"},
        0x23: {"name": "extra 24", "type": "value"},
        0x24: {"name": "extra 25", "type": "value"},
        0x25: {"name": "extra 26", "type": "value"},
        0x26: {"name": "extra 27", "type": "value"},
        0x27: {"name": "extra 28", "type": "value"},
        0x28: {"name": "extra 29", "type": "value"},
        0x29: {"name": "extra 30", "type": "value"},
        0x2A: {"name": "extra 31", "type": "value"},
        0x2B: {"name": "extra 32", "type": "value"},
        0x2C: {"name": "left turn", "type": "value"},
        0x2D: {"name": "right turn", "type": "value"},
        0x2E: {"name": "jump land slow", "type": "value"},
        0x2F: {"name": "jump land running", "type": "value"},
        0x30: {"name": "jump land hard", "type": "value"},
        0x31: {"name": "stop from full speed", "type": "value"},
        0x32: {"name": "stop from slow speed", "type": "value"},
        0x33: {"name": "running 180 change", "type": "value"},
        0x34: {"name": "player 9", "type": "value"},
        0x35: {"name": "player 10", "type": "value"},
        0x36: {"name": "player 11", "type": "value"},
        0x37: {"name": "player 12", "type": "value"},
        0x38: {"name": "player 13", "type": "value"},
        0x39: {"name": "player 14", "type": "value"},
        0x3A: {"name": "lean left slow", "type": "value"},
        0x3B: {"name": "lean left medium", "type": "value"},
        0x3C: {"name": "lean left fast", "type": "value"},
        0x3D: {"name": "lean right slow", "type": "value"},
        0x3E: {"name": "lean right medium", "type": "value"},
        0x3F: {"name": "lean right fast", "type": "value"},
    },
    "particle": {
        0x01: {"name": "output rate", "type": "value"},
        0x02: {"name": "output rate spread", "type": "value"},
        0x03: {"name": "lifetime", "type": "value"},
        0x04: {"name": "lifetime spread", "type": "value"},
        0x05: {"name": "clones (list)", "type": "set", "of": "particle"},
        0x06: {"name": "activation range", "type": "value"},
        0x07: {"name": "deactivation range", "type": "value"},
        0x08: {"name": "primary start velocity", "type": "value"},
        0x09: {"name": "primary start velocity spread", "type": "value"},
        0x0A: {"name": "primary start gravity", "type": "value"},
        0x0B: {"name": "primary start drag", "type": "value"},
        0x0C: {"name": "primary start color", "type": "value", "of": "color"},
        0x0D: {"name": "primary start color spread", "type": "value", "of": "color"},
        0x0E: {"name": "primary start size", "type": "value"},
        0x0F: {"name": "primary start size spread", "type": "value"},
        0x10: {"name": "primary end velocity", "type": "value"},
        0x11: {"name": "primary end velocity spread", "type": "value"},
        0x12: {"name": "primary end gravity", "type": "value"},
        0x13: {"name": "primary end drag", "type": "value"},
        0x14: {"name": "primary end color", "type": "value", "of": "color"},
        0x15: {"name": "primary end color spread", "type": "value", "of": "color"},
        0x16: {"name": "primary end size", "type": "value"},
        0x17: {"name": "primary end size spread", "type": "value"},
        0x18: {"name": "emitter spread x", "type": "value"},
        0x19: {"name": "emitter spread y", "type": "value"},
        0x1A: {"name": "emitter spread z", "type": "value"},
        0x1B: {"name": "angular spread x", "type": "value"},
        0x1C: {"name": "angular spread y", "type": "value"},
        0x1D: {"name": "visual radius", "type": "value"},
        0x1E: {"name": "cut-scene ignore", "type": "value"},
    },
    "MATH OPS": {
        0x01: {"name": "Normalized Angle", "type": "value"},
    },
    "MemCard": {
        0x01: {"name": "Unplugged", "type": "value"},
        0x02: {"name": "Free Space", "type": "value"},
        0x03: {"name": "Status", "type": "value"},
        0x04: {"name": "Auto-Save", "type": "value"},
        0x05: {"name": "Auto-Load", "type": "value"},
        0x06: {"name": "Current Slot", "type": "value"},
        0x07: {"name": "Current Slot Size", "type": "value"},
        0x08: {"name": "Auto-Format", "type": "value"},
        0x09: {"name": "Auto-Delete", "type": "value"},
        0x0A: {"name": "Saved Language", "type": "value"},
        0x0B: {"name": "Current Slot Percent Complete", "type": "value"},
        0x0C: {"name": "Auto-Create", "type": "value"},
        0x0D: {"name": "Current Slot Game Time", "type": "value"},
        0x0E: {"name": "Changed State", "type": "value"},
    },
    "FOG": {
        0x01: {"name": "vertex fog distance", "type": "value"},
        0x02: {"name": "vertex fog color", "type": "value", "of": "color"},
        0x03: {"name": "pixel fog/DOF distance", "type": "value"},
        0x04: {"name": "pixel fog/DOF cutoff intensity", "type": "value"},
        0x05: {"name": "pixel fog toggle", "type": "value"},
        0x06: {"name": "DOF bluriness factor", "type": "value"},
        0x07: {"name": "pixel fog/DOF color", "type": "value", "of": "color"},
        0x08: {"name": "bloom toggle", "type": "value"},
        0x09: {"name": "bloom add factor", "type": "value"},
        0x0A: {"name": "bloom halo size", "type": "value"},
    },
    "rumble": {
        0x01: {"name": "low frequency", "type": "value"},
        0x02: {"name": "high frequency", "type": "value"},
        0x03: {"name": "duration", "type": "value"},
        0x04: {"name": "radius", "type": "value"},
        0x05: {"name": "attenuation", "type": "value"},
        0x06: {"name": "time remaining", "type": "value"},
    },
}

SHOW_NAME_ONLY = True
TFBTOOL_MEMBER_FORMATTING = True

# Reference.scope -- which element a reference picks out of a set
# (0 = the set itself, no element picked).
SCOPE_LABELS = {
    1: "first",
    2: "last",
    3: "random",
}

# Types that have no members of their own. A `sub` on one of these picks a
# component out of it (e.g. the x of a sprite's location pair), which is
# itself a plain value.
SCALAR_TYPES = {"value", "angle", "color", "position"}


def member_field(type_name: str | None, index: int) -> dict[str, str] | None:
    """The BINDINGS entry for field `index` of `type_name`, if it is known."""
    bindings = BINDINGS.get(type_name) if type_name is not None else None
    return bindings.get(index) if bindings is not None else None


@dataclass(frozen=True)
class ResolvedType:
    """What a reference ultimately names: a type, and whether it is a whole
    set of them or a single one."""

    type: str | None  # None when it could not be resolved
    is_set: bool = False

    @override
    def __str__(self) -> str:
        if self.type is None:
            return "<unknown>"
        return f"set::{self.type}" if self.is_set else self.type

    def member_type(self, index: int) -> "ResolvedType":
        """This type's field `index` -- the type `.member`/`.sub` selects."""
        field = member_field(self.type, index)

        if field is None:
            if self.type in SCALAR_TYPES:
                return ResolvedType("value")
            return ResolvedType(None)

        if field.get("type") == "set":
            return ResolvedType(field.get("of"), is_set=True)

        # A plain value is the end of the line, but some of them are really a
        # colour or an x/y pair and `sub` picks one component out: "of" says
        # which table names those components, so `tint color`'s sub 0x04
        # resolves to the `a` of BINDINGS["color"].
        return ResolvedType(field.get("of", field.get("type")))  # "value"


@dataclass
class Reference:
    raw: int = 0x00  # the 32-bit little-endian value R, kept in sync by update_raw
    index: int = 0  # R >> 14
    member: int = 0  # (R >> 8) & 0x3F  -- field within the target
    scope: int = 0  # (R >> 6) & 3
    sub: int = 0  # R & 0x3F

    kind: ReferenceType = ReferenceType.NULL

    builtin_kind: BuiltinType | None = (
        None  # resolved builtin kind (None for not builtin)
    )

    slot: int | None = None  # table index used for the lookup (None for null/builtin)
    entry: StringTableEntry | None = None  # resolved entry (None for null/builtin)

    context: "ParserContext | None" = None  # script's parser context

    @classmethod
    def createSimple_local(
        cls,
        local_refs: StringTable,
        slot: int,
    ) -> "Reference":
        index = slot + LOCAL_BASE

        entry = local_refs.get(slot)

        member = 0
        scope = 0  # @1 @2 @3 (fist, last, random)
        sub = 0

        raw = (index << 14) | (member << 8) | (scope << 6) | sub

        return cls(
            raw=raw,
            index=index,
            member=0,
            scope=0,
            sub=0,
            # --
            kind=ReferenceType.LOCAL,
            builtin_kind=None,
            slot=slot,
            entry=entry,
        )

    def __post_init__(self) -> None:
        # Enable the __setattr__ hook only once every field exists, then compose
        # `raw` from the values the caller passed.
        object.__setattr__(self, "_raw_sync", True)
        self.update_raw()

    @override
    def __setattr__(self, name: str, value: object) -> None:
        # dataclass __init__ assigns fields one at a time, so the _raw_sync guard
        # keeps us from composing a raw out of half-initialised state;
        # __post_init__ does that once at the end.
        syncing = name in _RAW_INPUTS and getattr(self, "_raw_sync", False)
        previous = getattr(self, name) if syncing else None

        super().__setattr__(name, value)

        if syncing:
            try:
                self.update_raw()
            except ValueError:
                object.__setattr__(self, name, previous)  # keep the object valid
                raise

    def update_raw(self) -> int:
        """Recompose `raw` (and `index`) from the current field values.

        `index` is derived from `kind` plus `slot`/`builtin_kind` whenever those
        say what it should be, so moving a reference to another table slot is
        enough to keep both `index` and `raw` right. Returns the new `raw`.
        """
        index = self.index

        if self.kind == ReferenceType.NULL:
            # A null reference is all-ones; that is what the bit-fields decode to.
            index, member, scope, sub = 0x3FFFF, 0x3F, 3, 0x3F
        else:
            member, scope, sub = self.member, self.scope, self.sub

            if self.kind == ReferenceType.BUILTIN and self.builtin_kind is not None:
                index = self.builtin_kind.value
            elif self.kind == ReferenceType.LOCAL and self.slot is not None:
                index = LOCAL_BASE + self.slot
            elif self.kind == ReferenceType.GLOBAL and self.slot is not None:
                index = self.slot

        for name, value, limit in (
            ("index", index, 0x3FFFF),
            ("member", member, 0x3F),
            ("scope", scope, 0x3),
            ("sub", sub, 0x3F),
        ):
            if not 0 <= value <= limit:
                raise ValueError(
                    f"reference {name} {value:#x} does not fit its bit-field "
                    + f"(0..{limit:#x})"
                )

        raw = (index << 14) | (member << 8) | (scope << 6) | sub

        # object.__setattr__, so writing these back does not re-enter update_raw.
        object.__setattr__(self, "index", index)
        object.__setattr__(self, "member", member)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "sub", sub)
        object.__setattr__(self, "raw", raw)

        return raw

    @classmethod
    def createSimple_global(
        cls,
        global_refs: StringTable,
        slot: int,
    ) -> "Reference":
        index = slot

        entry = global_refs.get(slot)

        member = 0
        scope = 0  # @1 @2 @3 (fist, last, random)
        sub = 0

        raw = (index << 14) | (member << 8) | (scope << 6) | sub

        return cls(
            raw=raw,
            index=index,
            member=0,
            scope=0,
            sub=0,
            # --
            kind=ReferenceType.GLOBAL,
            builtin_kind=None,
            slot=slot,
            entry=entry,
        )

    @classmethod
    def createSimple_builtin(
        cls,
        builtin_type: BuiltinType,
    ) -> "Reference":
        index = builtin_type.value

        member = 0
        scope = 0  # @1 @2 @3 (fist, last, random)
        sub = 0

        raw = (index << 14) | (member << 8) | (scope << 6) | sub

        return cls(
            raw=raw,
            index=index,
            member=0,
            scope=0,
            sub=0,
            # --
            kind=ReferenceType.BUILTIN,
            builtin_kind=builtin_type,
            slot=None,
            entry=None,
        )

    @classmethod
    def read(
        cls,
        reader: "BinaryReader",
        global_refs: StringTable,
        local_refs: StringTable,
        context: "ParserContext | None" = None,
    ) -> "Reference":
        """Parse a 4-byte TFB-Script variable reference.

        Args:
            reader: BinaryReader positioned at the reference.
            global_refs: the script's 2nd string table (globals) for name resolution.
            local_refs: the script's 3rd string table (locals) for name resolution.
            context: the script's parser context, used to resolve the type of
                some builtins (e.g. "[~subset]") from prior opcodes.
        Returns:
            A Reference with the decoded bit-fields and a resolved `name`.
        """
        if reader.size_remaining() < 4:
            raise ValueError("a reference is 4 bytes, not enough bytes remaining")

        raw = reader.read_u32()
        fields = {
            "raw": raw,
            "index": raw >> 0xE,
            "member": (raw >> 0x8) & 0x3F,  # member index (applied first)
            "scope": (raw >> 0x6) & 3,  # mode
            "sub": raw & 0x3F,  # member index (applied last)
        }
        index = fields["index"]

        if raw == NULL_REF:
            return cls(
                **fields,
                builtin_kind=None,
                kind=ReferenceType.NULL,
                slot=None,
                entry=None,
                context=context,
            )

        if index >= BUILTIN_BASE:
            return cls(
                **fields,
                kind=ReferenceType.BUILTIN,
                builtin_kind=BuiltinType(index),
                slot=None,
                entry=None,
                context=context,
            )

        if index < LOCAL_BASE:
            entry = global_refs.get(index)
            return cls(
                **fields,
                kind=ReferenceType.GLOBAL,
                builtin_kind=None,
                slot=index,
                entry=entry,
                context=context,
            )

        slot = index - LOCAL_BASE
        entry = local_refs.get(slot)
        return cls(
            **fields,
            kind=ReferenceType.LOCAL,
            builtin_kind=None,
            slot=slot,
            entry=entry,
            context=context,
        )

    def write(self, f: BinaryIO) -> None:
        if self.kind == ReferenceType.BUILTIN and self.builtin_kind is None:
            raise ValueError("builtin reference has no builtin_kind")
        if self.kind in (ReferenceType.GLOBAL, ReferenceType.LOCAL):
            if self.slot is None:
                raise ValueError(f"{self.kind.name.lower()} reference has no slot")
        elif self.kind not in (ReferenceType.NULL, ReferenceType.BUILTIN):
            raise ValueError(f"Reference has unknown kind {self.kind}")

        write_u32(f, self.update_raw())

    @override
    def __str__(self) -> str:
        if self.kind == ReferenceType.NULL:  # Never seen a use of that ¯\_(ツ)_/¯
            return "<null>"

        if self.kind == ReferenceType.GLOBAL:
            assert self.entry is not None
            s = variable_global(
                self.entry.name if SHOW_NAME_ONLY else self.entry.string
            )
            if self.entry.category == "set":
                s = f" [{s}]"

        elif self.kind == ReferenceType.LOCAL:
            assert self.entry is not None
            s = variable(self.entry.name if SHOW_NAME_ONLY else self.entry.string)
            if self.entry.category == "set":
                s = f" [{s}]"

        elif self.kind == ReferenceType.BUILTIN:
            assert (
                self.builtin_kind is not None
            )  # should never be None for BUILTIN kind

            if TFBTOOL_MEMBER_FORMATTING and self.builtin_kind == BuiltinType.SELF:
                if self.member or self.sub:
                    s = builtin("my")
                else:
                    s = builtin("myself")
            else:
                s = builtin(BUILTIN_LABELS[self.builtin_kind])

        else:
            raise ValueError(f"Reference has unknown kind {self.kind}")

        if self.member:
            if self.builtin_kind == BuiltinType.MESSAGE_VALUE:
                # message value will always resolve to "value" wich is not in the bindings, so we suppress the warning here because its intended behavior
                s += self._get_member_string(suppressWarnings=True) or ""
            else:
                s += self._get_member_string() or ""

        if self.scope:
            # On a set, the scope picks one element out of it, e.g.
            # "first in [players]". `member` above still selects the set
            # itself, while `sub` below applies to the picked element. What it
            # means on anything else is unknown, so leave those as a raw "@N".
            if self._selects_from_set():
                label = SCOPE_LABELS.get(self.scope, str(self.scope))
                s = f"{keyword(f'{label} in')} {s.lstrip(' ')}"
            else:
                s += f"@{self.scope}"

        if self.sub:
            s += self._get_sub_string()

        return s

    def _get_sub_string(self) -> str:
        """The component `sub` picks out, named when whatever it applies to has
        a name for it -- the `a` of a tint colour, the `x` of a sprite's
        location -- and the raw index when it does not."""
        try:
            applies_to = self.resolve_type(apply_sub=False).type
        except ValueError:
            applies_to = None  # a builtin with no producer in reach

        field = member_field(applies_to, self.sub)

        if field is None or field.get("name") is None:
            return f".sub[{self.sub:#04x}]"

        return f".{field['name']}"

    def _selects_from_set(self) -> bool:
        """Whether what `scope` picks from is a set: the member it selects, or,
        with no member, the reference's own target."""
        if self.member:
            my_field = member_field(self.get_resolved_type(), self.member)
            return my_field is not None and my_field.get("type") == "set"

        return self._target_is_set()

    def _target_is_set(self) -> bool:
        """Whether the reference's own target (before `member`) is a set."""
        if self.kind == ReferenceType.BUILTIN:
            return self.builtin_kind == BuiltinType.SUBSET

        return self.entry is not None and self.entry.category == "set"

    def _get_member_string(self, suppressWarnings=False) -> str | None:
        my_type = self.get_resolved_type()

        if my_type is not None:
            my_bindings = BINDINGS.get(my_type)

            if my_bindings is not None:
                my_field = member_field(my_type, self.member)

                if my_field is not None:
                    label = my_field.get("name")
                    type_ = my_field.get("type")

                    if TFBTOOL_MEMBER_FORMATTING:
                        if (
                            self.kind == ReferenceType.BUILTIN
                            and self.builtin_kind == BuiltinType.SELF
                        ):
                            if type_ == "set":
                                return f" [{label}]"
                            else:
                                return f" {label}"
                        else:
                            if type_ == "set":
                                return f"'s [{label}]"
                            else:
                                return f"'s {label}"

                    else:
                        if type_ == "set":
                            return f".[{label}]"
                        else:
                            return f".{label}"
                else:
                    if not suppressWarnings:
                        print(
                            "WARN: cant resolve binding for",
                            my_type,
                            "member",
                            hex(self.member),
                            "entry",
                            self.entry,
                            file=sys.stderr,
                        )

            else:
                if not suppressWarnings:
                    print(
                        "WARN: cant resolve bindings for type",
                        '"' + my_type + '"',
                        "entry",
                        self.entry,
                        "field",
                        hex(self.member),
                        file=sys.stderr,
                    )

        return f".field[{self.member:#04x}]"

    def resolve_type(self, apply_sub: bool = True) -> ResolvedType:
        """The type this reference *ultimately* names, following the whole
        chain: target -> `member` -> `scope` -> `sub`.

        e.g. "first in return point's [waypoints]" starts at the actor
        variable "return point", takes its `waypoints` member (a set of
        waypoints), then `scope` picks one out of it -> a single "waypoint".

        `get_resolved_type` only gives the type of the target the chain starts
        at ("actor" in that example), which is what a `member` index is looked
        up against.

        `apply_sub=False` stops before `sub`, for the ops where `sub` is not a
        member selection: on a "find subset" set it names the field to filter
        on, so "my [waypoints].sub[0x01]" is still a set of waypoints there.
        """
        resolved = ResolvedType(self.get_resolved_type(), self._target_is_set())

        if self.member:
            # NOTE: a member on a set variable applies to its elements, so the
            # member's own kind is what we report -- same as `_selects_from_set`.
            resolved = resolved.member_type(self.member)

        if self.scope and resolved.is_set:
            # The scope picks one element out of the set (first/last/random).
            # On anything else its meaning is unknown, so leave the type alone.
            resolved = ResolvedType(resolved.type)

        if self.sub and apply_sub:
            resolved = resolved.member_type(self.sub)

        return resolved

    def get_final_type(self, apply_sub: bool = True) -> str | None:
        """The name of the type `resolve_type` lands on, e.g. "waypoint"."""
        return self.resolve_type(apply_sub).type

    def get_resolved_type(self) -> str | None:
        """The type of the target this reference starts at, *before* `member`,
        `scope` and `sub` are applied. Use `resolve_type` for the end of the
        chain."""
        # A builtin resolves through the op that produced it, and that op's own
        # operand can be the same builtin again -- `control [~controlled]`
        # nested inside `control [~controlled]` resolves via
        # nearest_ancestor(OpControl), which hands back the same producer every
        # time, so the chain never advances. Guard re-entry and report the type
        # as unknown rather than recursing forever.
        if id(self) in _RESOLVING:
            return None

        _RESOLVING.add(id(self))
        try:
            return self._get_resolved_type()
        finally:
            _RESOLVING.discard(id(self))

    def _get_resolved_type(self) -> str | None:
        if self.kind == ReferenceType.NULL:
            return "null"

        if self.kind == ReferenceType.BUILTIN:
            if self.builtin_kind == BuiltinType.SELF:
                return "actor"
            elif self.builtin_kind == BuiltinType.SUBSET:
                from tfbscript.opcodes import OpCheckFOV, OpFindSubset

                producer = self._builtin_find_producer((OpCheckFOV, OpFindSubset))

                if isinstance(producer, OpFindSubset):
                    return producer.set_ref.get_final_type(apply_sub=False)
                else:
                    return producer.target_ref.get_final_type()

            elif self.builtin_kind == BuiltinType.MESSAGE_VALUE:
                return "value"  # TODO: maybe we can resolve here??? seems kinda hard to do, since the message value is set by the sender and we don't have that context here

            elif self.builtin_kind == BuiltinType.FOUND_VARIABLE:
                # Not tested on real scripts cus couldnt find one
                from tfbscript.opcodes import OpFindVariable

                producer = self._builtin_find_producer(OpFindVariable)
                return producer.var_ref.get_final_type()

            elif self.builtin_kind == BuiltinType.EACH:
                from tfbscript.opcodes import OpForEach

                producer = self._builtin_find_producer(OpForEach)
                return producer.set_ref.get_final_type()

            elif self.builtin_kind == BuiltinType.CONTROLLED:
                from tfbscript.opcodes import OpControl, OpSpawnActor

                producer = self._builtin_find_producer((OpControl, OpSpawnActor))

                if isinstance(producer, OpControl):
                    return producer.target.get_final_type()
                else:
                    return producer.clone_ref.get_final_type()

            else:
                raise ValueError(
                    f"Reference is a builtin of kind {self.builtin_kind} but has no type resolution implemented"
                )

        if self.kind in (ReferenceType.GLOBAL, ReferenceType.LOCAL):  # variable
            if self.entry is not None:
                return self.entry.type
            else:
                raise ValueError("Reference has no entry to resolve type")

        return None  # Should never reach here

    def _builtin_find_producer(
        self, opcode_types: type[_OpcodeT] | tuple[type[_OpcodeT], ...]
    ):
        if self.context is None:
            raise ValueError(
                f"Reference {self.builtin_kind} is a builtin (and a field on it is used) but has no context to resolve its type"
            )
        producer = self.context.nearest_ancestor(opcode_types)
        if producer is None:
            raise ValueError(
                f"Reference {self.builtin_kind} is a builtin (and a field on it is used) but has no enclosing op to resolve its type"
            )

        return producer
