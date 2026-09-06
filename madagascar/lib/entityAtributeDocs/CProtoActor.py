import math
import struct
BASE_OFFSET = 0x1AC  # object-relative offset of byte 0 of the copied block
HEADER_SKIP = 0

CPROTOACTOR_ATTR1_FIELDS: dict[str, tuple[int, str] | tuple[int, str, int]] = {
    "solid_collision": (0x1B0, "flag", 0),
    "wall_climber": (0x1B0, "flag", 1),
    "wall_collision": (0x1B0, "flag", 2),
    "no_shadow": (0x1B0, "flag", 3),
    "visible_on_radar": (0x1B0, "flag", 4),
    "cut_scene_ignore": (0x1B0, "flag", 5),
    "ignores_ground_color": (0x1B0, "flag", 6),
    "tilts_with_ground": (0x1B0, "flag", 7),
    "mesh_collider_flag": (0x1B0, "flag", 8),  # AND +0x2C8 != 0, not available here
    "triangles_collide_flag": (0x1B0, "flag", 9),  # AND +0x2C8 != 0, not available here
    "activation_range": (0x1B4, "float"),
    "deactivation_range": (0x1B8, "float"),
    "cone_color": (0x1BC, "uint32"),
    "blip_color": (0x1C4, "uint32"),
    "activation_range_fade_percent": (0x1C8, "roundfloat"),
    "jump_coast_frames": (0x1F0, "roundfloat"),
    "jump_delay": (0x1F4, "roundfloat"),
    "health": (0x1F8, "roundfloat"),
    "move_type": (0x1FC, "roundfloat"),
    "ground_top_speed": (0x200, "float"),
    "ground_turn_rate": (0x204, "float"),
    "cone_length": (0x20C, "float"),
    "initial_jump_velocity": (0x218, "float"),
    "up_top_speed": (0x21C, "float"),
    "up_acceleration": (0x220, "float"),
    "down_acceleration": (0x224, "float"),
    "down_top_speed": (0x228, "float"),
    "bounce_restitution": (0x22C, "float"),
    "weight": (0x230, "float"),
    "ground_acceleration": (0x234, "float"),
    "ground_deceleration": (0x238, "float"),
    "air_top_speed": (0x23C, "float"),
    "air_acceleration": (0x240, "float"),
    "air_deceleration": (0x244, "float"),
    "X_offset": (0x254, "float"),
    "Y_offset": (0x258, "float"),
    "Z_offset": (0x25C, "float"),
    "air_turn_rate": (0x260, "float"),
    "H_extent": (0x248, "float"),
    "W_extent": (0x24C, "float"),
    "L_extent": (0x250, "float"),
    # unlike health/move_type/etc., id decodes to 0 under "roundfloat" no
    # matter what -- a small raw int (1-5, per the attached script) reads
    # as a subnormal float that always rounds to 0. Stored as a true int32,
    # not float32-encoded like most of this block.
    "id": (0x284, "int32"),
}

# fields known (from disassembly) to live *outside* the command-1 block --
# not parseable from this data, listed here purely so callers don't go
# looking for them in this blob.
CPROTOACTOR_FIELDS_NOT_IN_ATTR1 = {
    "tint_color": 0x2EC,  # set by a different command
    "altitude": 0x2C8,  # computed: conditionally reads through an override pointer
    "animation_rate_multiplier": 0x2C8,  # same override pointer as altitude
    # mesh_collider / triangles_collide (flag bits 8/9 above) also gate on
    # this same +0x2C8 pointer being non-null -- see CPROTOACTOR_ATTR1_FIELDS note.
}


def parse_CProtoActor_attribute1(data: bytes) -> dict[str, int | None | bool]:
    """
    Decode CProtoActor's stream "attribute 1" payload -- i.e.
    RW_strfunc_CreateEntity_Attribute.data for command==1 under class
    "CProtoActor" -- into named actor-stat fields.

    Returns a dict of field name -> decoded value (float / int / bool),
    or None for any field whose offset falls outside the given data.
    """
    payload = data[HEADER_SKIP:]
    result: dict[str, int | None | bool] = {}
    flags = None

    for name, spec in CPROTOACTOR_ATTR1_FIELDS.items():
        offset, kind = spec[0], spec[1]
        rel: int = offset - BASE_OFFSET
        if rel < 0 or rel + 4 > len(payload):
            result[name] = None
            continue

        if kind == "flag" and len(spec) == 3:
            if flags is None:
                flags = struct.unpack_from("<I", payload, rel)[0]
            bit = spec[2]
            result[name] = bool((flags >> bit) & 1)
        elif kind == "float":
            result[name] = struct.unpack_from("<f", payload, rel)[0]
        elif kind == "int32":
            result[name] = struct.unpack_from("<i", payload, rel)[0]
        elif kind == "roundfloat":
            fval = struct.unpack_from("<f", payload, rel)[0]
            if math.isfinite(fval):
                result[name] = round(fval)
            else:
                # bytes aren't a sane float (NaN/Inf) -- fall back to a raw
                # int32 reinterpretation rather than crashing; some records
                # apparently don't store this field as float32
                result[name] = struct.unpack_from("<i", payload, rel)[0]
        elif kind == "uint32":
            result[name] = struct.unpack_from("<I", payload, rel)[0]

    return result


CPROTOACTOR_ATTRIBUTES = {
    1: {
        "source": "GHIDRA",
        "name": "Actor Stats Block",
        "description": (
            "Blind copy of ~0x114 bytes into the live actor at object-offset "
            "0x1AC..0x2C0 (Game.exe FUN_0042e810, case 1). Packs health, "
            "move type, activation/deactivation range, jump/ground/air movement "
            "stats, weight, bounce restitution, X/Y/Z offset, W/L/H extent, "
            "cone color/length, blip color, and a flags dword covering solid "
            "collision, wall climber/collision, no shadow, visible on radar, "
            "cut-scene ignore, ignores ground color, tilts with ground, and "
            "the mesh/triangles collider bits. See parse_CProtoActor_attribute1()."
        ),
        "data": {"type": "CProtoActorStatsBlock"},
    },
}
