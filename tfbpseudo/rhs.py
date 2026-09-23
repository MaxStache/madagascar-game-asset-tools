"""Right-hand-side operands, spelled the same way by the compiler and the decompiler.

A TFB-Script RHS is one term -- an immediate or a reference -- optionally
followed by an operator and a second term. TfbPseudo spells those:

    5                   int                 tag 0x00
    1.5                 float               tag 0x10
    random(5)           random ceiling      tag 0x01 / 0x11
    color(r, g, b, a)   rgba                tag 0x20
    pair(x, y)          two int16s          tag 0x30
    Zoo Loop            reference           tag 0x02
    @myself * 2         expression          reference, operator, one term

Only a reference can take an operator tail, because that is all the format
stores: the engine's reader (TFBScript::readRHS, see tfbscript/rhs.py) looks
for the tail after a reference tag and nowhere else, and the tail's second
operand is a plain term rather than another expression.
"""

import math
from collections.abc import Callable
from typing import cast

from tfbpseudo.errors import CompileError, DecompileError
from tfbpseudo.lexer import Token, synth_token
from tfbpseudo.references import SET_OPEN
from tfbscript.opcodes.enums import RelOp
from tfbscript.reference import Reference as TFBReference
from tfbscript.rhs import Rhs

# Tag bytes, mirroring the reader in tfbscript/rhs.py. The high nibble picks
# the kind; TAG_RANDOM is a modifier bit and only means anything on int/float.
TAG_INT = 0x00
TAG_RANDOM = 0x01
TAG_REFERENCE = 0x02
TAG_FLOAT = 0x10
TAG_COLOR = 0x20
TAG_PAIR = 0x30

OPERATOR_BY_TOKEN: dict[str, int] = {"+": 0x00, "-": 0x01, "*": 0x02, "/": 0x03}
TOKEN_BY_OPERATOR: dict[int, str] = {
    operator: token for token, operator in OPERATOR_BY_TOKEN.items()
}

# The comparison a `check value` makes, taken straight off RelOp so the two
# spellings cannot drift: <=, ==, >=, <, >, !=.
REL_OP_BY_TOKEN: dict[str, RelOp] = {op.symbol(): op for op in RelOp}

RANDOM_CALL = "random"
COLOR_CALL = "color"
PAIR_CALL = "pair"
CALLS = (RANDOM_CALL, COLOR_CALL, PAIR_CALL)

INT_MIN, INT_MAX = -0x8000_0000, 0x7FFF_FFFF
CHANNEL_MIN, CHANNEL_MAX = 0x00, 0xFF
PAIR_MIN, PAIR_MAX = -0x8000, 0x7FFF

# Reads the reference starting at a position and says where it ended, i.e.
# Compiler.read_ref -- a reference is a whole `target.member#scope:sub` chain,
# so an RHS cannot know on its own where one stops.
ReadRefFn = Callable[[list[Token], int], tuple[TFBReference, int]]
# The inverse, i.e. Decompiler.ref_tokens.
RefTokensFn = Callable[[TFBReference], list[Token]]


class _Cursor:
    """Walks the tokens of one argument."""

    def __init__(self, tokens: list[Token], read_ref: ReadRefFn):
        self.tokens = tokens
        self.read_ref = read_ref
        self.pos = 0

    def peek(self, ahead: int = 0) -> Token | None:
        index = self.pos + ahead
        return self.tokens[index] if index < len(self.tokens) else None

    def next(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def at_op(self, *values: str, ahead: int = 0) -> bool:
        token = self.peek(ahead)
        return token is not None and token.kind == "OP" and token.value in values

    def take_ref(self) -> TFBReference:
        ref, self.pos = self.read_ref(self.tokens, self.pos)
        return ref

    def error(self, msg: str) -> CompileError:
        """A CompileError pointing at the current token, or at the last one when
        the argument ran out."""
        token = self.peek() or self.tokens[-1]
        return CompileError(msg, token.line, token.col)


# ----- the operator tail the format needs -----

# What a reference RHS can land on without the engine reading an operator and
# a second operand after it. readRHS (Game.exe 0043fd20) takes that 6-byte
# tail only when its gate is-a `value`, and the gate is the descriptor of the
# reference it has just read -- so it is what the reference lands on that
# decides, not what is being assigned to.
#
# Read off the shipped scripts: of the 46,964 reference RHS in the 1147 files
# under Levels/, all 39,865 that land on a value, actor, angle, sprite,
# waypoint, particle or attachment carry the tail, and all 6,402 that land on
# a colour or a 2D pair do not. The seven that go the other way are cases our
# own reader mis-parses -- see Rhs._tail_follows, which says as much.
#
# This is why the shipped scripts are full of `+ 0`: it is not arithmetic, it
# is the six bytes the engine is going to read whether or not anything wrote
# them. Leave them out and the engine reads the next instruction's bytes as
# the tail.
TAILLESS_TYPES = frozenset({"color", "2D"})

FILLER_OPERATOR = OPERATOR_BY_TOKEN["+"]


def takes_operator_tail(rhs: Rhs) -> bool:
    """Whether the engine will read an operator and a second operand after
    `rhs`, and the compiler therefore has to write them.

    A reference whose type cannot be worked out answers no: it is the honest
    answer where the type is unknown, and it leaves what the script already
    says alone -- the shipped scripts have fourteen of those, all writing a
    field of a builtin that has no binding.
    """
    if rhs.kind != "reference" or not isinstance(rhs.value, TFBReference):
        return False

    try:
        landed = rhs.value.resolve_type().type
    except ValueError:
        return False

    return landed is not None and landed not in TAILLESS_TYPES


def with_operator_tail(rhs: Rhs) -> Rhs:
    """`rhs` with the tail the engine is going to read: `+ 0`, which leaves
    the value it stands for alone."""
    return Rhs(
        TAG_REFERENCE,
        "expression",
        rhs.value,
        operator=FILLER_OPERATOR,
        rhs=Rhs(TAG_INT, "int", 0),
    )


def is_filler_tail(rhs: Rhs) -> bool:
    """Whether `rhs` is a reference plus the tail the format needs, rather
    than arithmetic the script meant.

    Exactly `+ 0` on an int, and only where `takes_operator_tail` would put it
    back -- so what this hides, the compiler writes again, byte for byte. The
    172 shipped tails that are `+ 0.0` or `- 0` are left alone: they do the
    same nothing, but not in a way this could re-create.
    """
    if rhs.kind != "expression" or rhs.operator != FILLER_OPERATOR:
        return False

    tail = rhs.rhs
    if tail is None or tail.kind != "int" or tail.value != 0 or tail.is_random:
        return False

    return takes_operator_tail(Rhs(TAG_REFERENCE, "reference", rhs.value))


def parse_rhs(tokens: list[Token], read_ref: ReadRefFn) -> Rhs:
    """The Rhs an argument's tokens spell out."""
    if not tokens:
        raise CompileError("expected a value", 0, 0)

    cursor = _Cursor(tokens, read_ref)
    left = _parse_term(cursor)

    t_operator = cursor.peek()
    if t_operator is None:
        # Nothing written after the value. If the engine is going to read an
        # operator and a second operand here anyway, they have to be in the
        # file, or it reads the next instruction instead -- which is the one
        # way a script that compiles can still crash the game.
        return with_operator_tail(left) if takes_operator_tail(left) else left

    if t_operator.kind != "OP" or t_operator.value not in OPERATOR_BY_TOKEN:
        raise cursor.error(f"unexpected {t_operator.value!r} after the value")

    if left.kind != "reference":
        raise CompileError(
            f"only a reference can be the left side of {t_operator.value!r}, "
            + f"{left.kind} values are stored on their own",
            t_operator.line,
            t_operator.col,
        )

    cursor.next()
    right = _parse_term(cursor)

    if cursor.peek() is not None:
        raise cursor.error(
            "an expression is one reference, one operator and one value, "
            + "there is no room for more"
        )

    return Rhs(
        TAG_REFERENCE,
        "expression",
        left.value,
        operator=OPERATOR_BY_TOKEN[t_operator.value],
        rhs=right,
    )


def parse_condition(
    tokens: list[Token], read_ref: ReadRefFn
) -> tuple[TFBReference, RelOp, Rhs]:
    """`lhs <op> rhs` -- the value being checked, how, and against what."""
    if not tokens:
        raise CompileError("expected a condition", 0, 0)

    lhs, pos = read_ref(tokens, 0)
    t_operator = tokens[pos] if pos < len(tokens) else None

    if (
        t_operator is None
        or t_operator.kind != "OP"
        or t_operator.value not in REL_OP_BY_TOKEN
    ):
        anchor = t_operator or tokens[-1]
        raise CompileError(
            f"expected one of {' '.join(REL_OP_BY_TOKEN)} "
            + "after the value being checked",
            anchor.line,
            anchor.col,
        )

    checked_against = tokens[pos + 1 :]
    if not checked_against:
        raise CompileError(
            f"expected a value after {t_operator.value!r}",
            t_operator.line,
            t_operator.col,
        )

    return lhs, REL_OP_BY_TOKEN[t_operator.value], parse_rhs(checked_against, read_ref)


def condition_tokens(
    lhs: TFBReference,
    rel_op: RelOp,
    rhs: Rhs,
    ref_tokens: RefTokensFn,
    drop_filler: bool = False,
) -> list[Token]:
    """The tokens parse_condition would have read this condition from."""
    return (
        ref_tokens(lhs)
        + [synth_token("OP", rel_op.symbol())]
        + rhs_tokens(rhs, ref_tokens, drop_filler)
    )


def _parse_term(cursor: _Cursor) -> Rhs:
    """One operand: an immediate, a call like `random(5)`, or a reference."""
    if cursor.peek() is None:
        raise cursor.error("expected a value")

    if cursor.at_op("+", "-"):
        t_sign = cursor.next()
        t_number = cursor.peek()

        if t_number is None or t_number.kind != "NUMBER":
            raise cursor.error(f"{t_sign.value!r} has to be followed by a number")

        return _number_term(cursor.next(), negative=t_sign.value == "-")

    token = cursor.peek()
    assert token is not None

    if token.kind == "NUMBER":
        return _number_term(cursor.next())

    # A variable may well be called `color`; only a following "(" makes it a call.
    if token.kind == "NAME" and token.value in CALLS and cursor.at_op("(", ahead=1):
        cursor.next()
        return _parse_call(cursor, token)

    # A set may be written in brackets, so a term can start with one: the
    # reference reader is the one that knows where the brackets end.
    if token.kind in ("NAME", "BUILTIN", "STRING") or cursor.at_op(SET_OPEN):
        return Rhs(TAG_REFERENCE, "reference", cursor.take_ref())

    cursor.next()
    raise CompileError(f"{token.value!r} is not a value", token.line, token.col)


def _number_term(token: Token, negative: bool = False) -> Rhs:
    """An int or float immediate, told apart by how the literal is written."""
    text = token.value
    sign = -1 if negative else 1

    if "." in text or "e" in text or "E" in text:
        return Rhs(TAG_FLOAT, "float", sign * float(text))

    value = sign * int(text, 0)

    if not INT_MIN <= value <= INT_MAX:
        raise CompileError(
            f"{value} does not fit the 32-bit int immediate", token.line, token.col
        )

    return Rhs(TAG_INT, "int", value)


def _parse_call(cursor: _Cursor, name: Token) -> Rhs:
    """`random(max)`, `color(r, g, b, a)` or `pair(x, y)`."""
    arguments = _call_arguments(cursor, name)

    if name.value == RANDOM_CALL:
        if len(arguments) != 1 or arguments[0].kind not in ("int", "float"):
            raise CompileError(
                f"{RANDOM_CALL}(max) takes one int or float ceiling",
                name.line,
                name.col,
            )

        # The engine rolls a uniform value in [0, max) for a random tag, so the
        # ceiling is just the immediate with the modifier bit set.
        ceiling = arguments[0]
        return Rhs(ceiling.tag | TAG_RANDOM, ceiling.kind, ceiling.value)

    if name.value == COLOR_CALL:
        channels = _int_arguments(name, arguments, 4, CHANNEL_MIN, CHANNEL_MAX)
        return Rhs(TAG_COLOR, "color", tuple(channels))

    axes = _int_arguments(name, arguments, 2, PAIR_MIN, PAIR_MAX)
    return Rhs(TAG_PAIR, "pair", tuple(axes))


def _call_arguments(cursor: _Cursor, name: Token) -> list[Rhs]:
    cursor.next()  # "("

    arguments: list[Rhs] = []
    while not cursor.at_op(")"):
        if cursor.peek() is None:
            raise cursor.error(f"unterminated `{name.value}(`")

        arguments.append(_parse_term(cursor))

        if cursor.at_op(","):
            cursor.next()
            continue

        if not cursor.at_op(")"):
            raise cursor.error(f"expected ',' or ')' in `{name.value}(`")

    cursor.next()  # ")"

    return arguments


def _int_arguments(
    name: Token, arguments: list[Rhs], count: int, low: int, high: int
) -> list[int]:
    if len(arguments) != count:
        raise CompileError(
            f"{name.value}() takes {count} whole numbers, got {len(arguments)}",
            name.line,
            name.col,
        )

    values: list[int] = []
    for argument in arguments:
        if argument.kind != "int" or not isinstance(argument.value, int):
            raise CompileError(
                f"{name.value}() takes whole numbers, got a {argument.kind}",
                name.line,
                name.col,
            )

        if not low <= argument.value <= high:
            raise CompileError(
                f"{name.value}() takes numbers from {low} to {high}, "
                + f"got {argument.value}",
                name.line,
                name.col,
            )

        values.append(argument.value)

    return values


def rhs_tokens(
    rhs: Rhs, ref_tokens: RefTokensFn, drop_filler: bool = False
) -> list[Token]:
    """The tokens parse_rhs would have read this Rhs from -- the inverse.

    `drop_filler` leaves out a `+ 0` that only exists because the format needs
    six bytes there. Nothing is lost by it: parse_rhs writes exactly that tail
    back in the same places, which is what makes leaving it out safe rather
    than merely tidier.
    """
    if drop_filler and is_filler_tail(rhs):
        return _reference_tokens(rhs, ref_tokens)

    if rhs.kind != "expression":
        return _term_tokens(rhs, ref_tokens)

    if rhs.operator is None or rhs.rhs is None:
        raise DecompileError("expression RHS has no operator or no second operand")

    operator = TOKEN_BY_OPERATOR.get(rhs.operator)
    if operator is None:
        raise DecompileError(f"RHS operator {rhs.operator:#04x} has no spelling")

    left = _reference_tokens(rhs, ref_tokens)

    return left + [synth_token("OP", operator)] + _term_tokens(rhs.rhs, ref_tokens)


def _term_tokens(rhs: Rhs, ref_tokens: RefTokensFn) -> list[Token]:
    if rhs.kind == "reference":
        return _reference_tokens(rhs, ref_tokens)

    if rhs.kind in ("int", "float"):
        if rhs.kind == "int":
            text = str(cast(int, rhs.value))
        else:
            text = float_text(cast(float, rhs.value))

        number = synth_token("NUMBER", text)

        # The random modifier is the only thing an immediate can carry.
        return _call_tokens(RANDOM_CALL, [number]) if rhs.is_random else [number]

    if rhs.kind == "color":
        channels = cast(tuple[int, int, int, int], rhs.value)
        return _call_tokens(
            COLOR_CALL, [synth_token("NUMBER", str(c)) for c in channels]
        )

    if rhs.kind == "pair":
        x, y = cast(tuple[int, int], rhs.value)
        return _call_tokens(
            PAIR_CALL, [synth_token("NUMBER", str(v)) for v in (x, y)]
        )

    raise DecompileError(f"RHS kind {rhs.kind} has no TfbPseudo spelling")


def _reference_tokens(rhs: Rhs, ref_tokens: RefTokensFn) -> list[Token]:
    if not isinstance(rhs.value, TFBReference):
        raise DecompileError(f"{rhs.kind} RHS does not hold a reference")

    return ref_tokens(rhs.value)


def _call_tokens(name: str, arguments: list[Token]) -> list[Token]:
    tokens = [synth_token("NAME", name), synth_token("OP", "(")]

    for i, argument in enumerate(arguments):
        if i:
            tokens.append(synth_token("OP", ","))
        tokens.append(argument)

    tokens.append(synth_token("OP", ")"))

    return tokens


def float_text(value: float) -> str:
    """A float literal that lexes back to the same value, i.e. one the NUMBER
    rule matches and that `_number_term` reads as a float rather than an int."""
    if not math.isfinite(value):
        raise DecompileError(f"float {value!r} has no TfbPseudo spelling")

    text = repr(float(value))

    if "." not in text and "e" not in text and "E" not in text:
        text += ".0"

    return text
