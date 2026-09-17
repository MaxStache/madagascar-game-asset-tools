"""References, spelled the same way by the compiler and the decompiler.

A reference names a target and then walks into it. The chain is the one
`Reference.resolve_type` follows -- target, `member`, `scope`, `sub` -- and
TfbPseudo spells it in that order:

    Zoo Loop                    the variable itself
    @myself.health              a field of the target       -> member
    my actor.waypoints#first    one element of a set        -> scope
    players#random:health       a field of the picked one   -> sub

A field is named the way the tfbscript BINDINGS name it, quoted when the name
is not a bare word (`."heading (OBSOLETE)"`), or given by index when the
script cannot resolve the type or the field has no name: `.field[0x2a]` and
`:sub[0x01]`, the spellings `Reference.__str__` prints.
"""

import re

from tfbscript.reference import (
    BINDINGS,
    SCOPE_LABELS,
    BuiltinType,
    ReferenceType,
    member_field,
)
from tfbscript.string_table import StringTable, StringTableEntry

BUILTIN_TOKENS: dict[str, BuiltinType] = {
    "@myself": BuiltinType.SELF,
    "@controlled": BuiltinType.CONTROLLED,
    "@each": BuiltinType.EACH,
    "@subset": BuiltinType.SUBSET,
    "@message": BuiltinType.MESSAGE_VALUE,
    "@found": BuiltinType.FOUND_VARIABLE,
}
BUILTIN_TOKEN_BY_KIND: dict[BuiltinType, str] = {
    kind: name for name, kind in BUILTIN_TOKENS.items()
}
NULL_BUILTIN_TOKEN = "@null"

# Which table to look a name up in, for the scripts that have the very same
# entry in both -- a bare name would always find the local one.
TABLE_TOKENS: dict[str, ReferenceType] = {
    "@local": ReferenceType.LOCAL,
    "@global": ReferenceType.GLOBAL,
}
TABLE_TOKEN_BY_KIND: dict[ReferenceType, str] = {
    kind: name for name, kind in TABLE_TOKENS.items()
}


def find_entry(
    local_refs: StringTable,
    global_refs: StringTable,
    name: str,
    table: ReferenceType | None = None,
) -> tuple[ReferenceType, int, StringTableEntry] | None:
    """The variable `name` picks out: its table, slot and entry.

    The whole "name::category::type" string wins over a bare name, and locals
    are searched before globals. `table` restricts the search to one of them,
    which is the only way to reach a global that a local of the same name
    shadows. Both directions go through this, so what the decompiler writes is
    by construction what the compiler will find.
    """
    tables = [
        (ReferenceType.LOCAL, local_refs),
        (ReferenceType.GLOBAL, global_refs),
    ]
    if table is not None:
        tables = [(kind, entries) for kind, entries in tables if kind == table]

    for match_string in (True, False):
        for kind, string_table in tables:
            for slot, entry in enumerate(string_table.entries):
                if (entry.string if match_string else entry.name) == name:
                    return kind, slot, entry

    return None

MEMBER_OP = "."
SCOPE_OP = "#"
SUB_OP = ":"
INDEX_OPEN = "["
INDEX_CLOSE = "]"

# The escape hatches, named after the way Reference spells them when it cannot
# name a field: `.field[0x2a]` and `:sub[0x01]`.
MEMBER_INDEX_WORD = "field"
SUB_INDEX_WORD = "sub"
SCOPE_INDEX_WORD = "scope"

# `#first` / `#last` / `#random`, the element a scope picks out of a set.
SCOPE_BY_NAME: dict[str, int] = {
    label: value for value, label in SCOPE_LABELS.items()
}

# member and sub are 6-bit fields, and 0 means "not used".
FIELD_MIN, FIELD_MAX = 0x01, 0x3F
# scope is 2 bits, and 0 means "not used".
SCOPE_MIN, SCOPE_MAX = 1, 3

# A name that can be written without quotes: words the lexer reads as IDENT or
# NUMBER, single spaces between them, the first one an IDENT. This is what
# Parser.parse_name glues back into a single NAME token.
BARE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?: [A-Za-z0-9_]+)*")


def member_index(type_name: str, name: str) -> int | None:
    """The index of the field `type_name` calls `name`, matching the BINDINGS
    label exactly or, failing that, ignoring case."""
    bindings = BINDINGS.get(type_name)
    if bindings is None:
        return None

    folded = name.casefold()
    fallback: int | None = None

    for index, field in bindings.items():
        label = field.get("name")
        if label == name:
            return index
        if fallback is None and label is not None and label.casefold() == folded:
            fallback = index

    return fallback


def member_name(type_name: str | None, index: int) -> str | None:
    """What `type_name` calls field `index`, if it has a name for it."""
    field = member_field(type_name, index)
    return field.get("name") if field is not None else None


def field_names(type_name: str) -> list[str]:
    """Every field name `type_name` knows, for error messages."""
    bindings = BINDINGS.get(type_name)
    if bindings is None:
        return []

    return [
        name for field in bindings.values() if (name := field.get("name")) is not None
    ]
