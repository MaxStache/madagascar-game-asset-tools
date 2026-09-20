"""What can be written at the cursor: the proposals the completer offers.

Every list comes from the registry that already owns it -- the methods from
METHOD_OPCODE_TABLE, their arguments from the specs those methods declare,
the fields from tfbscript's BINDINGS, the variables from the globals and
locals blocks of the text being edited -- so a new opcode, a new enum member
or a newly declared variable is completable without anyone touching this file.

There is no Qt in here: it is (source, position) in and proposals out, which
is also how it is tested. What surrounds the cursor is read off the line the
cursor is on, so a call whose arguments are wrapped across lines is completed
as if it were a statement -- the decompiler writes one statement per line.
"""

# pyright: basic

import re
from dataclasses import dataclass
from enum import IntEnum

from tfbpseudo.arguments import (
    Argument,
    Choice,
    Comparison,
    Condition,
    Number,
    Ref,
    Text,
    Value,
)
from tfbpseudo.compiler import METHOD_OPCODE_TABLE, MethodSpec
from tfbpseudo.references import (
    BARE_NAME,
    BUILTIN_TOKENS,
    NULL_BUILTIN_TOKEN,
    SCOPE_BY_NAME,
    TABLE_TOKENS,
    member_index,
)
from tfbpseudo.rhs import CALLS, REL_OP_BY_TOKEN
from tfbscript.opcodes import enums
from tfbscript.reference import BINDINGS, ResolvedType

# The shape of a name the lexer reads as one: words joined by single spaces.
NAME = r"[A-Za-z_][A-Za-z0-9_]*(?: [A-Za-z0-9_]+)*"

SECTIONS = ("globals", "locals", "prescript", "startup", "shutdown", "update")
BEHAVIOR_WORD = "behavior"

# `end`, `continue` and `break` are only ever the second half of a `flow`, so
# they are proposed after that word and nowhere else.
FLOW_WORD = "flow"
FLOW_MODES = ("end", "continue", "break")
ELSE_WORD = "else"
FLOW_WORDS = (FLOW_WORD, *FLOW_MODES, ELSE_WORD)  # all of them, to highlight

# What a name cannot start with, which is how `flow ` is told from `ground `:
# one is a keyword with a word of its own to come, the other is half of
# `ground top speed`.
KEYWORDS = (*SECTIONS, BEHAVIOR_WORD, *FLOW_WORDS)

# The builtins whose type is fixed wherever they are written.
BUILTIN_TYPES = {"@myself": "actor", "@message": "value"}

# The rest take theirs from the op that produced them, which is the block they
# are being written inside: `@each` in a `forEach(players, ...)` is one of the
# players. Each entry says which argument of which method to read it off.
PRODUCERS: dict[str, tuple[tuple[str, int], ...]] = {
    "@controlled": (("control", 0), ("spawnActor", 0)),
    "@each": (("forEach", 0),),
    "@subset": (("findSubset", 0), ("checkFOV", 2)),
    "@found": (("findVariable", 0),),
}

# The first thing an argument names, which is what its type starts at.
FIRST_REFERENCE = re.compile(r'@?[A-Za-z_][A-Za-z0-9_ ]*|"[^"\n]*"')

# What a proposal can put in `key`: punctuation that stands for it on its
# own, the way "!" stands for the layout preset. It is not part of any name,
# which is what makes it usable as a shorthand -- and what means the scanner
# below has to be told about it.
KEY_CHARS = "!"

# The trailing name the cursor is in the middle of. Names can have spaces in
# them, so this runs back over words until it hits something that cannot be
# part of one -- an operator, a bracket, a quote. A builtin is one word, and
# a bare "@" counts as the start of one so that typing it narrows to those.
PREFIX = re.compile(
    r"([" + KEY_CHARS + r"]|@[A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_ ]*)$"
)

# The two declaration blocks, kept apart: which one a variable is in says
# who owns it, and a local is the only kind this script has to create.
DECLARATION_BLOCK = re.compile(r"\b(globals|locals)\s*\{([^}]*)\}", re.DOTALL)
DECLARATION_OPEN = re.compile(r"\b(?:globals|locals)\s*\{")
QUOTED = re.compile(r'"([^"\n]*)"')
# A behavior block's name, which the compiler declares as a local of its own.
BEHAVIOR = re.compile(r'\bbehavior\s+(?:"([^"\n]*)"|(' + NAME + r'))\s*\{')
# The `flow` a mode word has to follow.
AFTER_FLOW = re.compile(r"\b" + FLOW_WORD + r"$")


@dataclass(frozen=True)
class Proposal:
    """One entry in the popup."""

    label: str
    detail: str = ""  # dimmed, on the right: a type, a signature, a kind
    insert: str | None = None  # what is typed for it, when not the label
    back: int = 0  # how far back into it the cursor lands, i.e. inside ()
    key: str | None = None # a key that shows the proposal at top when matches EXACTLY

    def text(self) -> str:
        return self.label if self.insert is None else self.insert


@dataclass(frozen=True)
class Completion:
    prefix: str  # what the proposals replace
    proposals: list[Proposal]
    # Whether this is a closed list -- the fields of a type, the members of an
    # enum, the words that can follow `flow` -- rather than everything that
    # could stand somewhere. A closed list is worth showing before anything
    # has been typed; the others would just be in the way.
    precise: bool = False


@dataclass(frozen=True)
class Variable:
    """A variable the text being edited declares."""

    name: str  # what it is written as: the part before the first "::"
    text: str  # the whole declaration string
    type: str | None  # the last "::" segment, i.e. "actor"
    category: str | None = None  # the middle one: "set", "user"
    scope: str = ""  # "global" or "local", after the block it is declared in
    line: int = 0  # 1-based, where it is declared

    def fits(self, expects: str | None) -> bool:
        """Whether this is the kind of variable an argument asks for.

        A set of actors is not an actor: `runAsPlayer` wants one of them and
        the membership ops want the set, so the two never stand in for each
        other.
        """
        if expects is None:
            return True

        if expects == "set":
            return self.category == "set"

        return self.type == expects and self.category != "set"

    def kind(self) -> str:
        """What it is, for the dimmed half of its entry."""
        if self.type is None:
            return "variable"

        return f"set of {self.type}" if self.category == "set" else self.type


def enum_members() -> list[str]:
    """Every name an enum argument accepts, e.g. `slow_move`, `randomly`."""
    names: set[str] = set()

    for value in vars(enums).values():
        if isinstance(value, type) and issubclass(value, IntEnum) and value is not IntEnum:
            names.update(member.name for member in value)

    return sorted(names, key=len, reverse=True)


# ----- reading what is around the cursor -----


def outside_strings(line: str) -> str | None:
    """`line` with whatever is inside quotes blanked out, or None when the
    cursor is inside a string -- where nothing is completed.

    Blanking keeps the length, so offsets into the answer are offsets into the
    line, and the quotes themselves stay to be read as delimiters.
    """
    out: list[str] = []
    in_string = False
    escaped = False

    for char in line:
        if not in_string:
            out.append(char)
            in_string = char == '"'
            continue

        if escaped:
            escaped = False
            out.append(" ")
        elif char == "\\":
            escaped = True
            out.append(" ")
        elif char == '"':
            in_string = False
            out.append('"')
        else:
            out.append(" ")

    return None if in_string else "".join(out)


def split_prefix(line: str) -> tuple[str, str]:
    """The name being typed at the end of `line`, and what is left to its left.

    Names have spaces in them, so `ground ` is half of `ground top speed` and
    goes on being the name. A keyword is not: after `flow ` what is being
    typed is the word that follows it.
    """
    match = PREFIX.search(line)
    prefix = match.group(1) if match else ""

    first, space, rest = prefix.partition(" ")
    if space and first in KEYWORDS:
        prefix = rest

    return prefix, line[: len(line) - len(prefix)]


def prefix_at(source: str, position: int) -> str:
    """The name being typed at `position`, which is what a proposal replaces."""
    line = outside_strings(source[:position].rsplit("\n", 1)[-1])
    if line is None:
        return ""

    return split_prefix(line)[0]


def in_comment(head: str, line: str) -> bool:
    """Whether `head` ends inside a comment, of either kind."""
    return "//" in line or head.rfind("/*") > head.rfind("*/")


def enclosing_call(line: str) -> tuple[str, int] | None:
    """The call the cursor is inside: its name and which argument it is on.

    `line` has had its strings blanked, so a bracket inside one cannot open a
    call that never closes.
    """
    stack: list[tuple[str, int]] = []

    for index, char in enumerate(line):
        if char == "(":
            match = PREFIX.search(line[:index])
            stack.append((match.group(1).strip() if match else "", 0))
        elif char == ")":
            if stack:
                stack.pop()
        elif char == "," and stack:
            name, argument = stack[-1]
            stack[-1] = (name, argument + 1)
        elif char in "{};":
            stack.clear()  # whatever came before, a new statement starts here

    return stack[-1] if stack else None


def open_blocks(head: str) -> list[str]:
    """The header of every block still open at the end of `head`.

    Outermost first, a header being whatever stands between the end of the
    last statement and the brace that opened the block: `behavior Patrol {`
    then `forEach(@subset, forward) {`.
    """
    stack: list[str] = []
    current: list[str] = []
    in_string = False
    escaped = False
    at = 0

    while at < len(head):
        char = head[at]

        if in_string:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            current.append(char)
        elif head.startswith("//", at):
            ended = head.find("\n", at)
            at = len(head) if ended < 0 else ended
            continue
        elif head.startswith("/*", at):
            ended = head.find("*/", at)
            at = len(head) if ended < 0 else ended + 2
            continue
        elif char == "{":
            stack.append("".join(current).strip())
            current = []
        elif char == "}":
            if stack:
                stack.pop()
            current = []
        elif char == ";":
            current = []
        else:
            current.append(char)

        at += 1

    return stack


def call_parts(header: str) -> tuple[str, list[str]] | None:
    """A block header read as a call: `forEach(@subset, forward)` becomes
    ("forEach", ["@subset", "forward"])."""
    opened = header.find("(")
    if opened < 0:
        return None

    name = PREFIX.search(header[:opened])
    if name is None:
        return None

    arguments: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False

    for char in header[opened + 1 :]:
        if in_string:
            in_string = char != '"'
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                break
            depth -= 1
        elif char == "," and depth == 0:
            arguments.append("".join(current))
            current = []
            continue

        current.append(char)

    arguments.append("".join(current))
    return name.group(1).strip(), arguments


def builtin_type(
    source: str, head: str, token: str, seen: tuple[str, ...] = ()
) -> str | None:
    """What a builtin names, where the cursor is.

    The fixed ones answer for themselves; the rest are answered by the
    enclosing op that produced them, innermost first, the way the script
    would answer at runtime.
    """
    fixed = BUILTIN_TYPES.get(token)
    if fixed is not None or token in seen:
        return fixed

    for header in reversed(open_blocks(head)):
        call = call_parts(header)
        if call is None:
            continue

        method, arguments = call
        for producer, index in PRODUCERS.get(token, ()):
            if method == producer and index < len(arguments):
                return argument_type(
                    source, head, arguments[index], (*seen, token)
                )

    return None


def argument_type(
    source: str, head: str, text: str, seen: tuple[str, ...] = ()
) -> str | None:
    """The type of the thing an argument starts at.

    Only what it starts at: `findSubset(players:health > 0)` picks players
    out by a field of theirs, and what comes back is still players.
    """
    found = FIRST_REFERENCE.search(text)
    if found is None:
        return None

    name = found.group().strip().strip('"')
    if name.startswith("@"):
        return builtin_type(source, head, name, seen)

    return variable_type(source, name)


def reference_parts(text: str) -> list[tuple[str, str]]:
    """The reference `text` ends with, as (operator, name) pairs.

    `@myself.waypoints#first` reads back as [("", "@myself"),
    (".", "waypoints"), ("#", "first")]; the first operator is always empty.
    """
    parts: list[tuple[str, str]] = []

    while True:
        text = text.rstrip()

        if text.endswith('"'):
            start = text.rfind('"', 0, len(text) - 1)
            if start < 0:
                break
            name, text = text[start + 1 : -1], text[:start]
        else:
            match = PREFIX.search(text)
            if match is None:
                break
            name, text = match.group(1).strip(), text[: match.start()]

        text = text.rstrip()
        operator = text[-1] if text[-1:] in (".", ":", "#") else ""
        parts.append((operator, name))

        if not operator:
            break
        text = text[:-1]

    parts.reverse()
    return parts


# ----- what the text being edited declares -----


def variables(source: str) -> list[Variable]:
    """Every variable `source` declares, in the order it declares them.

    The behaviors count: the compiler declares each one as a local of type
    "behavior", which is how `setBehavior(Patrol)` finds the block named
    Patrol, so they are completed alongside the rest.
    """
    found: list[Variable] = []
    seen: set[str] = set()

    def add(
        name: str,
        text: str,
        kind: str | None,
        category: str | None,
        scope: str,
        at: int,
    ) -> None:
        if name and name not in seen:
            seen.add(name)
            found.append(
                Variable(
                    name,
                    text,
                    kind,
                    category,
                    scope,
                    source.count("\n", 0, at) + 1,
                )
            )

    for block in DECLARATION_BLOCK.finditer(source):
        scope = "global" if block.group(1) == "globals" else "local"

        for entry in QUOTED.finditer(block.group(2)):
            text = entry.group(1)
            parts = [part.strip() for part in text.split("::")]
            add(
                parts[0],
                text,
                parts[-1] if len(parts) > 1 else None,
                parts[1] if len(parts) > 2 else None,
                scope,
                block.start(2) + entry.start(),
            )

    # A behavior block declares the behavior, and the compiler puts it in the
    # locals beside the rest.
    for block in BEHAVIOR.finditer(source):
        name = (block.group(1) or block.group(2)).strip()
        add(name, name, "behavior", None, "local", block.start())

    return found


def variable_type(source: str, spelling: str) -> str | None:
    """The type of the variable written as `spelling` -- its bare name, or the
    whole "name::category::type" string the ambiguous ones are written as."""
    for variable in variables(source):
        if spelling in (variable.name, variable.text):
            return variable.type

    return None


def in_declarations(head: str) -> bool:
    """Whether the cursor is inside a globals or locals block, where the only
    thing that can be written is a quoted declaration."""
    opens = list(DECLARATION_OPEN.finditer(head))
    return bool(opens) and "}" not in head[opens[-1].end() :]


# ----- the proposals themselves -----


def field_kind(field: dict[str, str]) -> str:
    kind = field.get("type", "")
    return f"set of {field.get('of')}" if kind == "set" else kind


def field_proposal(name: str, detail: str) -> Proposal:
    """A field, quoted when its name is not one the lexer reads as a name."""
    written = name if BARE_NAME.fullmatch(name) else f'"{name}"'
    return Proposal(name, detail, insert=written)


def fields_of(type_name: str) -> list[Proposal]:
    bindings = BINDINGS.get(type_name, {})
    return [
        field_proposal(name, field_kind(field))
        for field in bindings.values()
        if (name := field.get("name")) is not None
    ]


def members(source: str, head: str, target: str) -> list[Proposal]:
    """The fields of whatever the reference ending `target` names.

    Only that type's fields: an actor's on an actor, a camera's on a camera.
    A type that cannot be worked out is offered nothing rather than
    everything -- a list of every field there is answers a question nobody
    asked, and hides the one that was.
    """
    parts = reference_parts(target)
    if not parts:
        return []

    base = parts[0][1]
    if base.startswith("@"):
        start = builtin_type(source, head, base)
    else:
        start = variable_type(source, base)

    resolved = ResolvedType(start)

    for operator, name in parts[1:]:
        if operator == "#":
            continue  # picks an element out of a set; the type is unchanged

        index = member_index(resolved.type, name) if resolved.type else None
        if index is None:
            return []

        resolved = resolved.member_type(index)

    if resolved.type is None:
        return []

    return fields_of(resolved.type)


def signature(spec: MethodSpec) -> str:
    """How a method is called, for the dimmed half of its entry."""
    names = [
        f"[{argument.name}]" if argument.optional else argument.name
        for argument in spec.arguments
    ]
    return f"({', '.join(names)})"


def values(
    source: str, expects: str | None = None, calls: bool = False
) -> list[Proposal]:
    """What can stand where a reference or a value is expected.

    `expects` is the kind of variable the argument names, for the arguments
    that always name the same kind: `playSound` is offered the sounds and
    nothing else. The builtins whose type is fixed are held to it as well,
    while the ones that take theirs from a surrounding op stay -- what `@each`
    is depends on the set being walked, so it could be the right thing.
    """
    proposals = [
        Proposal(variable.name, variable.kind())
        for variable in variables(source)
        if variable.fits(expects)
    ]
    proposals += [
        Proposal(token, "builtin")
        for token in BUILTIN_TOKENS
        if expects is None or BUILTIN_TYPES.get(token) in (None, expects)
    ]
    proposals.append(Proposal(NULL_BUILTIN_TOKEN, "builtin"))
    proposals += [Proposal(token, "table") for token in TABLE_TOKENS]

    if calls:
        proposals += [
            Proposal(call, "call", insert=f"{call}()", back=1) for call in CALLS
        ]

    return proposals


def arguments(source: str, method: str, index: int) -> tuple[list[Proposal], bool]:
    """What the `index`th argument of `method` accepts."""
    if method in CALLS:
        return [], True  # random, color and pair all take plain numbers

    spec = METHOD_OPCODE_TABLE.get(method)
    argument = (
        spec.arguments[index]
        if spec is not None and index < len(spec.arguments)
        else None
    )

    if isinstance(argument, Choice):
        return [
            Proposal(member.name, argument.enum.__name__) for member in argument.enum
        ], True

    if isinstance(argument, (Text, Number, Comparison)):
        return [], True  # a quoted string, a plain number, a bare operator

    if isinstance(argument, Ref):
        return values(source, argument.expects), argument.expects is not None

    # A value, a condition, or an argument of a method nobody has heard of:
    # anything a right-hand side can be.
    return values(source, calls=True), False


def statements() -> list[Proposal]:
    """What can start a line: a method call, or one of the words that frame
    the script."""
    proposals = [
        Proposal(name, signature(spec), insert=f"{name}()", back=1)
        for name, spec in sorted(METHOD_OPCODE_TABLE.items())
    ]
    proposals += [Proposal(word, "section") for word in SECTIONS]
    proposals.append(Proposal(BEHAVIOR_WORD, "section"))
    proposals += [Proposal(word, "flow") for word in (FLOW_WORD, ELSE_WORD)]
    return proposals


def context(source: str, head: str, before: str) -> tuple[list[Proposal], bool]:
    """The proposals for a cursor with `before` to its left on its line, and
    whether they are a closed list."""
    if in_declarations(head):
        return [], True  # the entries there are quoted strings, not names

    stripped = before.rstrip()

    if stripped.endswith((".", ":")):
        return members(source, head, stripped[:-1]), True

    if stripped.endswith("#"):
        return [Proposal(name, "scope") for name in SCOPE_BY_NAME], True

    call = enclosing_call(before)
    if call is not None:
        return arguments(source, *call)

    if AFTER_FLOW.search(stripped):
        return [Proposal(word, "flow") for word in FLOW_MODES], True

    proposals = statements()
    basic_layout = """globals {
}

locals {
}

prescript {
    startup {
    }

    shutdown {
    }

    update {
    }
}"""
    proposals.append(
        Proposal(
            "Basic Layout",
            insert=basic_layout,
            detail="Preset",
            key="!"
        )
    )

    behavior_preset = """behavior BEHAVIOR_NAME {
}"""
    proposals.append(
        Proposal(
            "Behavior",
            insert=behavior_preset,
            detail="Preset",
            key="behav"
        )
    )

    return proposals, False


def ranked(prefix: str, proposals: list[Proposal]) -> list[Proposal]:
    """The proposals `prefix` matches: the ones starting with it first, then
    the ones merely containing it, i.e. `speed` finding `ground top speed`."""
    if not prefix:
        return proposals

    folded = prefix.casefold()
    key_matched: list[Proposal] = []
    starting: list[Proposal] = []
    containing: list[Proposal] = []

    for proposal in proposals:
        label = proposal.label.casefold()
        if proposal.key and proposal.key.casefold() == folded:
            key_matched.append(proposal)
        if label.startswith(folded):
            starting.append(proposal)
        elif folded in label:
            containing.append(proposal)

    return key_matched + starting + containing


def argument_help(argument: Argument) -> str:
    """What one argument takes, in a few words.

    Read off the argument's own class, so a method that gains an argument
    says so here without anyone writing it down twice.
    """
    if isinstance(argument, Choice):
        what = f"one of {argument.choices()}"
    elif isinstance(argument, Ref):
        what = f"a {argument.expects}" if argument.expects else "a reference"
    elif isinstance(argument, Condition):
        what = "a condition, as in `a > b`"
    elif isinstance(argument, Comparison):
        what = "a comparison: " + " ".join(REL_OP_BY_TOKEN)
    elif isinstance(argument, Text):
        what = "a quoted string"
    elif isinstance(argument, Number):
        what = "a number" if argument.is_float else "a whole number"
    elif isinstance(argument, Value):
        what = "a value, a reference or an expression"
    else:
        what = "an argument"

    return f"{what}, optional" if argument.optional else what


def method_help(name: str, spec: MethodSpec) -> str:
    """A method, its arguments, and what it is made of."""
    lines = [
        f"{name}{signature(spec)}",
        f'compiles to the "{spec.op_name}" opcode',
    ]

    if spec.arguments:
        width = max(len(argument.name) for argument in spec.arguments)
        lines.append("")
        lines += [
            f"  {argument.name:<{width}}   {argument_help(argument)}"
            for argument in spec.arguments
        ]

    return "\n".join(lines)


def variable_help(variable: Variable) -> str:
    """A declared name: what kind it is and where it comes from."""
    return "\n".join(
        [
            variable.name,
            f"{variable.scope} {variable.kind()}".strip(),
            f"declared on line {variable.line}",
        ]
    )


def help_at(source: str, position: int) -> str:
    """What there is to say about whatever `position` is on, or nothing.

    Methods first: a script is free to declare a variable named after one,
    and it is the method that is being read when the cursor is on the word
    in front of a bracket.
    """
    name = name_at(source, position)
    if not name:
        return ""

    spec = METHOD_OPCODE_TABLE.get(name)
    if spec is not None:
        return method_help(name, spec)

    for variable in variables(source):
        if name in (variable.name, variable.text):
            return variable_help(variable)

    return ""


def name_at(source: str, position: int) -> str:
    """The whole name the cursor is inside or beside, quoted one included.

    Unlike the completion prefix this reaches past the cursor as well: what is
    wanted here is the name as written, not the part of it typed so far.
    """
    start = source.rfind("\n", 0, position) + 1
    ending = source.find("\n", position)
    line = source[start : ending if ending >= 0 else len(source)]
    column = position - start

    for quoted in QUOTED.finditer(line):
        if quoted.start() < column < quoted.end():
            return quoted.group(1)

    for word in re.finditer(r"@?" + NAME, line):
        if word.start() <= column <= word.end():
            return word.group().strip()

    return ""


def definition_of(source: str, name: str) -> int | None:
    """The line `name` is declared on: its entry, or its behavior block."""
    for variable in variables(source):
        if name in (variable.name, variable.text):
            return variable.line

    return None


def call_at(source: str, position: int) -> tuple[str, int] | None:
    """The call the cursor is inside: the method, and the argument it is on.

    The same reading the completer works from, for whoever wants to say what
    the call takes rather than what could be written next.
    """
    line = outside_strings(source[:position].rsplit("\n", 1)[-1])
    if line is None:
        return None

    return enclosing_call(line)


def keyed(prefix: str, proposals: list[Proposal]) -> bool:
    """Whether `prefix` is the key of one of `proposals`.

    A key is typed on purpose and means one proposal, so the one character of
    it is enough to show the popup -- the same standing a closed list has.
    """
    folded = prefix.casefold()
    return any(
        proposal.key and proposal.key.casefold() == folded for proposal in proposals
    )


def completions(source: str, position: int) -> Completion:
    """What can be written at `position` in `source`."""
    head = source[:position]
    line = outside_strings(head.rsplit("\n", 1)[-1])

    if line is None or in_comment(head, line):
        return Completion("", [])

    prefix, before = split_prefix(line)
    proposals, precise = context(source, head, before)

    return Completion(
        prefix,
        ranked(prefix, proposals),
        precise or keyed(prefix, proposals),
    )
