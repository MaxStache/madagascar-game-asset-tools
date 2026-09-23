"""References, spelled the same way by the compiler and the decompiler.

A reference names a target and then walks into it. The chain is the one
`Reference.resolve_type` follows -- target, `member`, `scope`, `sub` -- and
TfbPseudo spells it in that order:

    Zoo Loop                    the variable itself
    @myself.health              a field of the target       -> member
    my actor.waypoints#first    one element of a set        -> scope
    players#random:health       a field of the picked one   -> sub

A set may be written in brackets, the way `Reference.__str__` prints one --
`[players]`, `@myself.[waypoints]#first` -- which says out loud that it is a
set of things rather than one thing. The brackets are optional and go around
the name alone, so `#first` and any field come after them.

A field is named the way the tfbscript BINDINGS name it, quoted when the name
is not a bare word (`."heading (OBSOLETE)"`), or given by index when the
script cannot resolve the type or the field has no name: `.field[0x2a]` and
`:sub[0x01]`, the spellings `Reference.__str__` prints.
"""

import re
from dataclasses import dataclass

from tfbscript.opcodes import (
    OpCheckFOV,
    OpCheckMessage,
    OpControl,
    OpFindSubset,
    OpFindVariable,
    OpForEach,
    OpSpawnActor,
)
from tfbscript.opcodes.base import Opcode, ParserContext
from tfbscript.reference import (
    BINDINGS,
    SCOPE_LABELS,
    BuiltinType,
    Reference,
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
    "@found_variable": BuiltinType.FOUND_VARIABLE,
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


@dataclass(frozen=True)
class BuiltinScope:
    """Where a builtin means anything: the ops that produce what it names."""

    producers: tuple[type[Opcode], ...]
    methods: tuple[str, ...]  # what TfbPseudo calls those ops, for the error
    stands_for: str

    def message(self, token: str) -> str:
        bodies = " or ".join(f"`{method}(...)`" for method in self.methods)
        return f"{token} is {self.stands_for}, so it only means anything inside {bodies}"


# Every builtin but `@myself` names something an enclosing op left behind, and
# outside that op's body there is nothing for it to name -- the engine reads
# whatever the last op of that kind happened to put there, so a stray `@each`
# is a bug rather than a value.
#
# Which op that is was read off the shipped scripts rather than guessed: of the
# 79,121 builtin references in the 1147 files under Levels/, every single one
# sits inside the body of an op listed here -- `@each` under a `forEach`
# (19,530 uses), `@found_variable` under a `findVariable` (4,360), `@message`
# under a `checkMessage` (1,030), `@subset` under a `findSubset` or a
# `checkFOV` (1,513), `@controlled` under a `control` or a `spawnActor`
# (2,821). `@myself` is the script's own actor, needs no producer, and is left
# out of here because it is legal anywhere.
#
# "Inside the body" is the rule, not "on the op": a producer's own arguments
# are read before its body opens, so the `@controlled` in `control(@controlled)`
# names an outer `control`, which is how the shipped scripts use it too.
BUILTIN_SCOPES: dict[BuiltinType, BuiltinScope] = {
    BuiltinType.CONTROLLED: BuiltinScope(
        producers=(OpControl, OpSpawnActor),
        methods=("control", "spawnActor"),
        stands_for="the actor the op took hold of",
    ),
    BuiltinType.EACH: BuiltinScope(
        producers=(OpForEach,),
        methods=("forEach",),
        stands_for="the element the loop is on",
    ),
    BuiltinType.SUBSET: BuiltinScope(
        producers=(OpFindSubset, OpCheckFOV),
        methods=("findSubset", "checkFOV"),
        stands_for="what the search found",
    ),
    BuiltinType.MESSAGE_VALUE: BuiltinScope(
        producers=(OpCheckMessage,),
        methods=("checkMessage",),
        stands_for="the value the message carried",
    ),
    BuiltinType.FOUND_VARIABLE: BuiltinScope(
        producers=(OpFindVariable,),
        methods=("findVariable",),
        stands_for="the variable the lookup found",
    ),
}


def builtin_out_of_scope(
    kind: BuiltinType, context: ParserContext | None
) -> BuiltinScope | None:
    """The scope a use of `kind` is outside of, or None when the use is fine.

    `context.open_opcodes` is the stack of ops whose body is being walked, so
    asking it for the nearest producer is the same question the engine answers
    at runtime. A builtin with no scope of its own -- `@myself` -- and a
    context that cannot say where it is are both fine by definition.
    """
    scope = BUILTIN_SCOPES.get(kind)

    if scope is None or context is None:
        return None

    if context.nearest_ancestor(scope.producers) is not None:
        return None

    return scope


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
# `[` and `]` do two jobs, told apart by where they are: after a name they are
# the raw index form, `field[0x2a]`, and around one they are the optional
# brackets a set may be written in, `[players]`.
INDEX_OPEN = "["
INDEX_CLOSE = "]"
SET_OPEN = INDEX_OPEN
SET_CLOSE = INDEX_CLOSE

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


def member_is_set(type_name: str | None, index: int) -> bool | None:
    """Whether field `index` of `type_name` holds a set, or None when the
    script has nothing to say about that field."""
    field = member_field(type_name, index)
    return field.get("type") == "set" if field is not None else None


def names_a_set(ref: Reference) -> bool | None:
    """Whether the target `ref` starts at -- before `.member`, `#scope` and
    `:sub` -- is a set, or None when the script cannot tell.

    Reference decides this for its own rendering, so ask it rather than
    repeating the rule here. The one thing it cannot know is
    `@found_variable`: a lookup lands on whatever it finds, which is a set as
    easily as a value.
    """
    if (
        ref.kind == ReferenceType.BUILTIN
        and ref.builtin_kind == BuiltinType.FOUND_VARIABLE
    ):
        return None

    return ref._target_is_set()  # pyright: ignore[reportPrivateUsage]


def field_names(type_name: str) -> list[str]:
    """Every field name `type_name` knows, for error messages."""
    bindings = BINDINGS.get(type_name)
    if bindings is None:
        return []

    return [
        name for field in bindings.values() if (name := field.get("name")) is not None
    ]
