"""Decode TFB-Script (Madagascar .ai) variable references.

A "reference" is the 4-byte operand the value opcodes (set value, check value,
create variable, set reference, find variable, ...) use to point at a variable.

The engine reads the 4 bytes as a little-endian uint32 R (Game.exe FUN_00432920)
and resolves it as a bit-field (FUN_00432f70):

    index  = R >> 14        # bits 31..14 : which object
    member = (R >> 8) & 0x3F  # bits 13..8  : field/member within that object
    scope  = (R >> 6) & 3     # bits  7..6  : owner/scope selector
    sub    =  R       & 0x3F  # bits  5..0  : extra sub-field selector

`index` selects the target (switch in FUN_00432f70):

    R == 0xFFFFFFFF                 -> null (no reference)
    0x3FFFA <= index <= 0x3FFFF     -> a built-in object (self, player, ...)
    index  <  0x3FC0D              -> GLOBAL symbol  -> table2[index]
    0x3FC0D <= index < 0x3FFFA      -> LOCAL  symbol  -> table3[index - 0x3FC0D]

The table2/table3 mapping is validated against shipped scripts: the six
consecutive `create variable` locals decode to consecutive table3 value entries,
and global refs walk table2 in order (actor/value pairs) as the logic expects.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Union

# --- constants from FUN_00432f70 ------------------------------------------
LOCAL_BASE = 0x3FC0D  # index >= this (and < BUILTIN_BASE) => script-local
BUILTIN_BASE = 0x3FFFA  # index >= this => engine built-in object
NULL_REF = 0xFFFFFFFF

# index -> built-in name. Each FUN_00433140(kind) call walks backward through
# enclosing scopes for the nearest one whose OWN category getter (vtbl+0x2c)
# returns `kind` -- these are not fixed global sentinels, they're dynamically
# resolved relative to where the reference appears (same mechanism as `self`).
BUILTINS = {
    0x3FFFF: "self",  # FUN_00433140(2)    -- confirmed: nearest enclosing actor scope
    0x3FFFE: "[~controlled]",  # FUN_00433140(0)     -- provisional builtin(0)
    0x3FFFD: "[~each]",  # FUN_00433140(0x65)  -- confirmed: nearest enclosing `for each`'s
    #   current item (for_each's own category getter, FUN_0043cc70,
    #   returns 0x65; seen in the wild assigned out of a for-each body)
    0x3FFFC: "[~subset]",  # FUN_00433140(3)     -- provisional builtin(3)
    0x3FFFB: "[~found]",  # FUN_00436e30()      -- provisional
    0x3FFFA: "[~found_variable]",  # FUN_00433140(6)     -- provisional builtin(6)
}

# A string table is a list of entries; each entry is either a plain str or a
# dict shaped like {"string": "...", ...} (as produced by readStringTable()).
TableEntry = Union[str, dict]
Table = Sequence[TableEntry]


@dataclass
class Reference:
    raw: int  # the 32-bit little-endian value R
    index: int  # R >> 14
    member: int  # (R >> 8) & 0x3F  -- field within the target
    scope: int  # (R >> 6) & 3
    sub: int  # R & 0x3F
    kind: str  # 'null' | 'builtin' | 'global' | 'local'
    slot: Optional[int]  # table index used for the lookup (None for null/builtin)
    name: str  # resolved name (or descriptive placeholder)

    def __str__(self) -> str:
        if self.kind == "null":
            return "<null>"

        s = self.name
        if self.member:
            if self.name.endswith("::sound"):  # type is sound
                if self.member == 1:
                    s += ".[volume]"
                elif self.member == 2:
                    s += ".[pitch]"
                elif self.member == 3:
                    s += ".[elapsed_time]"
                elif self.member == 4:
                    s += ".[remaining_time]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::sprite"):  # type is sprite
                if self.member == 0x02:
                    s += ".[location]"  # Pair16, sub 1 = x, sub 2 = y
                elif self.member == 0x05:
                    s += ".[tint_color]"
                elif self.member == 0x03:
                    s += ".[scale]"
                elif self.member == 0x04:
                    s += ".[rotation]"
                elif self.member == 0x06:
                    s += ".[justification]"
                elif self.member == 0x0A:
                    s += ".[pixel_extends]"
                elif self.member == 0x07:
                    s += ".[visible]"
                elif self.member == 0x09:
                    s += ".[priority]"
                elif self.member == 0x01:
                    s += ".[content]"
                elif self.member == 0x08:
                    s += ".[clones]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::actor"):  # type is actor
                ACTOR_FIELDS = {
                    0x01: "health",
                    0x02: "waypoints (list)",
                    0x03: "origin",
                    0x04: "destination (point)",
                    0x05: "heading (OBSOLETE)",
                    0x06: "facing (OBSOLETE)",
                    0x07: "current speed",
                    0x08: "altitude",
                    0x09: "attach points (list)",
                    0x0A: "activation range fade percent",
                    0x0B: "activation range",
                    0x0C: "deactivation range",
                    0x0D: "clones (list)",
                    0x0E: "ground top speed",
                    0x0F: "ground turn rate",
                    0x10: "ground acceleration",
                    0x11: "ground deceleration",
                    0x12: "move type",
                    0x13: "air top speed",
                    0x14: "air turn rate",
                    0x15: "air acceleration",
                    0x16: "air deceleration",
                    0x17: "jump delay",
                    0x18: "initial jump velocity",
                    0x19: "jump coast frames",
                    0x1A: "up top speed",
                    0x1B: "up acceleration",
                    0x1C: "down top speed",
                    0x1D: "down acceleration",
                    0x1E: "animation rate multiplier",
                    0x1F: "weight",
                    0x20: "bounce restitution",
                    0x21: "X offset", # Extend box X
                    0x22: "Y offset", # Extend box Y
                    0x23: "Z offset", # Extend box Z 
                    0x24: "W extend", # Extend box W extend
                    0x25: "L extend", # Extend box L extend
                    0x26: "H extend", # Extend box H extend
                    0x27: "cone angle",
                    0x28: "cone length",
                    0x29: "cone sweep offset",
                    0x2A: "blip color",
                    0x2B: "cone color",
                    0x2C: "solid collision",
                    0x2D: "wall collision",
                    0x2E: "visible on radar",
                    0x2F: "wall climber",
                    0x30: "cut-scene ignore",
                    0x31: "ignore ground color",
                    0x32: "tilts with ground",
                    0x33: "no shadow",
                    0x34: "ID",
                    0x35: "mesh collider",
                    0x36: "triangles collide",
                    0x37: "tint color",
                    0x38: "turrets (list)",
                }
                if self.member in ACTOR_FIELDS:
                    s += f".[{ACTOR_FIELDS[self.member]}]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::controller"):  # type is controller
                CONTROLLER_FIELDS = {
                    0x01: "circle button",
                    0x02: "triangle button",
                    0x03: "X button",
                    0x04: "square button",
                    0x05: "select button",
                    0x06: "start button",
                    0x07: "L1 button",
                    0x08: "R1 button",
                    0x09: "L2 button",
                    0x0A: "R2 button",
                    0x0B: "DPad left",
                    0x0C: "DPad right",
                    0x0D: "DPad up",
                    0x0E: "DPad down",
                    0x0F: "analog1 left",
                    0x10: "analog1 right",
                    0x11: "analog1 up",
                    0x12: "analog1 down",
                    0x13: "analog2 left",
                    0x14: "analog2 right",
                    0x15: "analog2 up",
                    0x16: "analog2 down",
                    0x17: "analog1 heading",
                    0x18: "analog1 magnitude",
                    0x19: "analog2 heading",
                    0x1A: "analog2 magnitude",
                    0x1B: "connection",
                }
                if self.member in CONTROLLER_FIELDS:
                    s += f".[{CONTROLLER_FIELDS[self.member]}]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::MemCard"):  # type is MemCard
                MEMCARD_FIELDS = {
                    0x01: "Unplugged",
                    0x02: "Free Space",
                    0x03: "Status",
                    0x04: "Auto-Save",
                    0x05: "Auto-Load",
                    0x06: "Current Slot",
                    0x07: "Current Slot Size",
                    0x08: "Auto-Format",
                    0x09: "Auto-Delete",
                    0x0A: "Saved Language",
                    0x0B: "Current Slot Percent Complete",
                    0x0C: "Auto-Create",
                    0x0D: "Current Slot Game Time",
                    0x0E: "Changed State",
                }
                if self.member in MEMCARD_FIELDS:
                    s += f".[{MEMCARD_FIELDS[self.member]}]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::MOTION BLUR"):  # type is MOTION BLUR
                MOTION_BLUR_FIELDS = {
                    0x01: "amount",
                    0x02: "offset-x",
                    0x03: "offset-y",
                    0x04: "scale x-axis",
                    0x05: "scale y-axis",
                    0x06: "scale",
                    0x07: "angle",
                }
                if self.member in MOTION_BLUR_FIELDS:
                    s += f".[{MOTION_BLUR_FIELDS[self.member]}]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::particle"):  # type is particle
                PARTICLE_FIELDS = {
                    0x01: "output rate",
                    0x02: "output rate spread",
                    0x03: "lifetime",
                    0x04: "lifetime spread",
                    0x05: "clones (list)",
                    0x06: "activation range",
                    0x07: "deactivation range",
                    0x08: "primary start velocity",
                    0x09: "primary start velocity spread",
                    0x0A: "primary start gravity",
                    0x0B: "primary start drag",
                    0x0C: "primary start color",
                    0x0D: "primary start color spread",
                    0x0E: "primary start size",
                    0x0F: "primary start size spread",
                    0x10: "primary end velocity",
                    0x11: "primary end velocity spread",
                    0x12: "primary end gravity",
                    0x13: "primary end drag",
                    0x14: "primary end color",
                    0x15: "primary end color spread",
                    0x16: "primary end size",
                    0x17: "primary end size spread",
                    0x18: "emitter spread x",
                    0x19: "emitter spread y",
                    0x1A: "emitter spread z",
                    0x1B: "angular spread x",
                    0x1C: "angular spread y",
                    0x1D: "visual radius",
                    0x1E: "cut-scene ignore",
                }
                if self.member in PARTICLE_FIELDS:
                    s += f".[{PARTICLE_FIELDS[self.member]}]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::camera"):  # type is particle
                CAMERA_FIELDS = {
                    0x01: "look from",
                    0x02: "look from horizontal offset",
                    0x03: "look from vertical offset",
                    0x04: "look from heading offset",
                    0x05: "look from heading relative",
                    0x06: "look at",
                    0x07: "look at horizontal offset",
                    0x08: "look at vertical offset",
                    0x09: "look at heading offset",
                    0x0A: "look at heading relative",
                    0x0B: "field of view",
                    0x0C: "laziness",
                    0x0D: "percent complete",
                    0x0E: "time remaining",
                    0x0F: "Vertical Follow At",
                    0x10: "Horizontal Follow",
                    0x11: "Current Facing",
                    0x12: "Vertical Follow From",
                    0x13: "pitch control",
                    0x14: "roll",
                }
                if self.member in CAMERA_FIELDS:
                    s += f".[{CAMERA_FIELDS[self.member]}]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::animation mapping"):  # type is animation mapping
                ANIMATION_MAPPING_FIELDS = {
                    0x01: "ambient",
                    0x02: "slowest move",
                    0x03: "slow move",
                    0x04: "fast move",
                    0x05: "jump",
                    0x06: "fall",
                    0x07: "youch", # hurt
                    0x08: "slide",
                    0x09: "attack 1",
                    0x0A: "attack 2",
                    0x0B: "tumble",
                    0x0C: "extra 1",
                    0x0D: "extra 2",
                    0x0E: "extra 3",
                    0x0F: "extra 4",
                    0x10: "extra 5",
                    0x11: "extra 6",
                    0x12: "extra 7",
                    0x13: "extra 8",
                    0x14: "extra 9",
                    0x15: "extra 10",
                    0x16: "extra 11",
                    0x17: "extra 12",
                    0x18: "extra 13",
                    0x19: "extra 14",
                    0x1A: "extra 15",
                    0x1B: "extra 16",
                    0x1C: "extra 17",
                    0x1D: "extra 18",
                    0x1E: "extra 19",
                    0x1F: "extra 20",
                    0x20: "extra 21",
                    0x21: "extra 22",
                    0x22: "extra 23",
                    0x23: "extra 24",
                    0x24: "extra 25",
                    0x25: "extra 26",
                    0x26: "extra 27",
                    0x27: "extra 28",
                    0x28: "extra 29",
                    0x29: "extra 30",
                    0x2A: "extra 31",
                    0x2B: "extra 32",
                    0x2C: "left turn",
                    0x2D: "right turn",
                    0x2E: "jump land slow",
                    0x2F: "jump land running",
                    0x30: "jump land hard",
                    0x31: "stop from full speed",
                    0x32: "stop from slow speed",
                    0x33: "running 180 change",
                    0x34: "player 9",
                    0x35: "player 10",
                    0x36: "player 11",
                    0x37: "player 12",
                    0x38: "player 13",
                    0x39: "player 14",
                    0x3A: "lean left slow",
                    0x3B: "lean left medium",
                    0x3C: "lean left fast",
                    0x3D: "lean right slow",
                    0x3E: "lean right medium",
                    0x3F: "lean right fast",
                }
                if self.member in ANIMATION_MAPPING_FIELDS:
                    s += f".[{ANIMATION_MAPPING_FIELDS[self.member]}]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::MATH OPS"):  # type is MATH OPS
                MATH_OPS_FIELDS = {
                    0x01: "Normalized Angle", #  assign an angle to it, read the wrapped-to-±180 value back
                }
                if self.member in MATH_OPS_FIELDS:
                    s += f".[{MATH_OPS_FIELDS[self.member]}]"
                else:
                    s += f".field[{self.member:#04x}]"
            elif self.name.endswith("::FOG"):  # type is FOG
                FOG_FIELDS = {
                    0x01: "vertex fog distance",
                    0x02: "vertex fog color",
                    0x03: "pixel fog/DOF distance",
                    0x04: "pixel fog/DOF cutoff intensity",
                    0x05: "pixel fog toggle",
                    0x06: "DOF bluriness factor",
                    0x07: "pixel fog/DOF color",
                    0x08: "bloom toggle",
                    0x09: "bloom add factor",
                    0x0a: "bloom halo size",
                }
                if self.member in FOG_FIELDS:
                    s += f".[{FOG_FIELDS[self.member]}]"
                else:
                    s += f".field[{self.member:#04x}]"
            else:
                s += f".field[{self.member:#04x}]"
        if self.sub:
            s += f".sub[{self.sub:#04x}]"
        if self.scope:
            s += f"@{self.scope}" # set / array / list index
        return s


def _entry_name(table: Optional[Table], idx: int) -> Optional[str]:
    if table is None or not (0 <= idx < len(table)):
        return None
    e = table[idx]
    return e["string"] if isinstance(e, dict) else str(e)


def parse_reference(
    data: bytes,
    offset: int = 0,
    table2: Optional[Table] = None,
    table3: Optional[Table] = None,
) -> Reference:
    """Parse a 4-byte TFB-Script variable reference.

    Args:
        data:   bytes containing the reference (>= 4 bytes from `offset`).
        offset: where the 4-byte reference starts.
        table2: the script's 2nd string table (globals) for name resolution.
        table3: the script's 3rd string table (locals) for name resolution.

    Returns:
        A Reference with the decoded bit-field and a resolved `name`.
    """
    if len(data) - offset < 4:
        raise ValueError("a reference is 4 bytes")

    R = int.from_bytes(data[offset : offset + 4], "little")
    index = R >> 14
    member = (R >> 8) & 0x3F
    scope = (R >> 6) & 3
    sub = R & 0x3F

    if R == NULL_REF:
        return Reference(R, index, member, scope, sub, "null", None, "<null>")

    if index >= BUILTIN_BASE:
        return Reference(
            R,
            index,
            member,
            scope,
            sub,
            "builtin",
            None,
            BUILTINS.get(index, f"builtin@{index:#x}"),
        )

    if index < LOCAL_BASE:
        name = _entry_name(table2, index)
        return Reference(
            R,
            index,
            member,
            scope,
            sub,
            "global",
            index,
            name if name is not None else f"global#{index}",
        )

    slot = index - LOCAL_BASE
    name = _entry_name(table3, slot)
    return Reference(
        R,
        index,
        member,
        scope,
        sub,
        "local",
        slot,
        name if name is not None else f"local#{slot}",
    )
