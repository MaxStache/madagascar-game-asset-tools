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
LOCAL_BASE   = 0x3FC0D   # index >= this (and < BUILTIN_BASE) => script-local
BUILTIN_BASE = 0x3FFFA   # index >= this => engine built-in object
NULL_REF     = 0xFFFFFFFF

# index -> built-in name. Each FUN_00433140(kind) call walks backward through
# enclosing scopes for the nearest one whose OWN category getter (vtbl+0x2c)
# returns `kind` -- these are not fixed global sentinels, they're dynamically
# resolved relative to where the reference appears (same mechanism as `self`).
BUILTINS = {
    0x3FFFF: "self",            # FUN_00433140(2)    -- confirmed: nearest enclosing actor scope
    0x3FFFE: "~controlled_actor",      # FUN_00433140(0)     -- provisional builtin(0)
    0x3FFFD: "~each",           # FUN_00433140(0x65)  -- confirmed: nearest enclosing `for each`'s
                                 #   current item (for_each's own category getter, FUN_0043cc70,
                                 #   returns 0x65; seen in the wild assigned out of a for-each body)
    0x3FFFC: "~found_subset",      # FUN_00433140(3)     -- provisional builtin(3)
    0x3FFFB: "~found",          # FUN_00436e30()      -- provisional 
    0x3FFFA: "~found_variable",      # FUN_00433140(6)     -- provisional builtin(6)
}

# A string table is a list of entries; each entry is either a plain str or a
# dict shaped like {"string": "...", ...} (as produced by readStringTable()).
TableEntry = Union[str, dict]
Table = Sequence[TableEntry]


@dataclass
class Reference:
    raw: int            # the 32-bit little-endian value R
    index: int          # R >> 14
    member: int         # (R >> 8) & 0x3F  -- field within the target
    scope: int          # (R >> 6) & 3
    sub: int            # R & 0x3F
    kind: str           # 'null' | 'builtin' | 'global' | 'local'
    slot: Optional[int] # table index used for the lookup (None for null/builtin)
    name: str           # resolved name (or descriptive placeholder)

    def __str__(self) -> str:
        if self.kind == "null":
            return "<null>"
        
        s = self.name
        if self.member:
            s += f".field[{self.member:#04x}]"
        if self.sub:
            s += f".sub[{self.sub:#04x}]"
        if self.scope:
            s += f"@{self.scope}"
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

    R = int.from_bytes(data[offset:offset + 4], "little")
    index  = R >> 14
    member = (R >> 8) & 0x3F
    scope  = (R >> 6) & 3
    sub    = R & 0x3F

    if R == NULL_REF:
        return Reference(R, index, member, scope, sub, "null", None, "<null>")

    if index >= BUILTIN_BASE:
        return Reference(R, index, member, scope, sub, "builtin", None,
                         BUILTINS.get(index, f"builtin@{index:#x}"))

    if index < LOCAL_BASE:
        name = _entry_name(table2, index)
        return Reference(R, index, member, scope, sub, "global", index,
                         name if name is not None else f"global#{index}")

    slot = index - LOCAL_BASE
    name = _entry_name(table3, slot)
    return Reference(R, index, member, scope, sub, "local", slot,
                     name if name is not None else f"local#{slot}")