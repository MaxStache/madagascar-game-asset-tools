"""Opcode arguments, spelled the same way by the compiler and the decompiler.

Nearly every opcode is a fixed list of operands, so rather than writing the two
directions out by hand for each one -- where they could drift apart -- an
opcode declares its operands once in `methods.py` and both handlers are built
from that declaration. Each Argument here knows how to read one argument's
tokens into the opcode's fields and how to write those fields back out.

An argument may be `optional`, in which case it is the trailing ones that go
missing: `spawnActor` has a byte that is only in some files, `useCamera` has a
second duration only for a real transition. `present` decides whether to write
one back out, and everything after an absent argument is absent too.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Any

from tfbpseudo.errors import CompileError, DecompileError
from tfbpseudo.lexer import Token, synth_token
from tfbpseudo.rhs import REL_OP_BY_TOKEN, float_text
from tfbscript.opcodes.base import Opcode
from tfbscript.opcodes.enums import RelOp

if TYPE_CHECKING:
    from tfbpseudo.compiler import Compiler
    from tfbpseudo.decompiler import Decompiler

@dataclass(frozen=True)
class Argument:
    """One argument of an opcode."""

    name: str  # the opcode field it sets, and what errors call it
    optional: bool = False
    default: Any = None  # what the field is when the argument is left out
    # For the opcodes whose payload shape is recorded in a private field
    # rather than shown by the argument's own value.
    present_if: Callable[[Opcode], bool] | None = None

    def read(
        self, tokens: list[Token], compiler: "Compiler"
    ) -> dict[str, object]:  # pragma: no cover - overridden
        raise NotImplementedError

    def write(
        self, opcode: Opcode, decompiler: "Decompiler"
    ) -> list[Token]:  # pragma: no cover - overridden
        raise NotImplementedError

    def absent(self) -> dict[str, object]:
        """The fields to set when this argument is not written."""
        return {self.name: self.default}

    def present(self, opcode: Opcode) -> bool:
        """Whether to write this argument back out."""
        if self.present_if is not None:
            return self.present_if(opcode)

        return getattr(opcode, self.name) != self.default

    def error(self, tokens: list[Token], msg: str) -> CompileError:
        anchor = tokens[0] if tokens else Token("EOF", "", 0, 0)
        return CompileError(f"{self.name}: {msg}", anchor.line, anchor.col)

    def one_token(self, tokens: list[Token], kind: str, what: str) -> Token:
        if len(tokens) != 1 or tokens[0].kind != kind:
            raise self.error(tokens, f"expected {what}")

        return tokens[0]


@dataclass(frozen=True)
class Ref(Argument):
    """A reference: `Zoo Loop`, `@myself.health`, `players#first`."""

    def read(self, tokens: list[Token], compiler: "Compiler") -> dict[str, object]:
        return {self.name: compiler.get_ref_by_tokens(tokens)}

    def write(self, opcode: Opcode, decompiler: "Decompiler") -> list[Token]:
        return decompiler.ref_tokens(getattr(opcode, self.name))


@dataclass(frozen=True)
class Value(Argument):
    """A right-hand side: an immediate, a reference, or an expression."""

    def read(self, tokens: list[Token], compiler: "Compiler") -> dict[str, object]:
        return {self.name: compiler.get_rhs_by_tokens(tokens)}

    def write(self, opcode: Opcode, decompiler: "Decompiler") -> list[Token]:
        return decompiler.rhs_tokens(getattr(opcode, self.name))


@dataclass(frozen=True)
class Condition(Argument):
    """`lhs <op> rhs` in one argument, setting three fields at once."""

    rel_op_name: str = "rel_op"
    rhs_name: str = "rhs"

    def read(self, tokens: list[Token], compiler: "Compiler") -> dict[str, object]:
        lhs, rel_op, rhs = compiler.get_condition_by_tokens(tokens)
        return {self.name: lhs, self.rel_op_name: rel_op, self.rhs_name: rhs}

    def absent(self) -> dict[str, object]:
        # All three fields keep whatever the opcode's dataclass defaults are.
        return {}

    def write(self, opcode: Opcode, decompiler: "Decompiler") -> list[Token]:
        return decompiler.condition_tokens(
            getattr(opcode, self.name),
            getattr(opcode, self.rel_op_name),
            getattr(opcode, self.rhs_name),
        )


@dataclass(frozen=True)
class Comparison(Argument):
    """A bare relational operator, for the ops that carry one on its own."""

    def read(self, tokens: list[Token], compiler: "Compiler") -> dict[str, object]:
        if len(tokens) != 1 or tokens[0].value not in REL_OP_BY_TOKEN:
            raise self.error(tokens, f"expected one of {' '.join(REL_OP_BY_TOKEN)}")

        return {self.name: REL_OP_BY_TOKEN[tokens[0].value]}

    def write(self, opcode: Opcode, decompiler: "Decompiler") -> list[Token]:
        rel_op: RelOp = getattr(opcode, self.name)
        return [synth_token("OP", rel_op.symbol())]


@dataclass(frozen=True)
class Choice(Argument):
    """One of an enum's members, written by name -- `slow_move`, `randomly` --
    or by its raw number when a file has one the enum has no name for."""

    enum: type[IntEnum] = RelOp

    def read(self, tokens: list[Token], compiler: "Compiler") -> dict[str, object]:
        if len(tokens) != 1 or tokens[0].kind not in ("NAME", "NUMBER", "STRING"):
            raise self.error(tokens, f"expected one of {self.choices()}")

        token = tokens[0]

        if token.kind == "NUMBER":
            try:
                return {self.name: self.enum(int(token.value, 0))}
            except ValueError:
                raise self.error(
                    tokens, f"{token.value} is not a {self.enum.__name__} value"
                ) from None

        folded = token.value.casefold()
        for member in self.enum:
            if member.name.casefold() == folded:
                return {self.name: member}

        raise self.error(
            tokens, f"{token.value!r} is not one of {self.choices()}"
        )

    def write(self, opcode: Opcode, decompiler: "Decompiler") -> list[Token]:
        value = getattr(opcode, self.name)

        if not isinstance(value, self.enum):
            return [synth_token("NUMBER", str(int(value)))]

        return [synth_token("NAME", value.name)]

    def choices(self) -> str:
        names = [member.name for member in self.enum]
        if len(names) > 6:
            return ", ".join(names[:6]) + f", ... ({len(names)} in all)"
        return ", ".join(names)


@dataclass(frozen=True)
class Text(Argument):
    """A quoted string the opcode stores verbatim."""

    def read(self, tokens: list[Token], compiler: "Compiler") -> dict[str, object]:
        return {self.name: self.one_token(tokens, "STRING", "a quoted string").value}

    def write(self, opcode: Opcode, decompiler: "Decompiler") -> list[Token]:
        return [synth_token("STRING", getattr(opcode, self.name))]


@dataclass(frozen=True)
class Number(Argument):
    """A plain number the opcode stores as-is, not a right-hand side."""

    is_float: bool = False

    def read(self, tokens: list[Token], compiler: "Compiler") -> dict[str, object]:
        negative = False
        rest = tokens

        if tokens and tokens[0].kind == "OP" and tokens[0].value in ("+", "-"):
            negative = tokens[0].value == "-"
            rest = tokens[1:]

        token = self.one_token(rest, "NUMBER", "a number")
        text = token.value

        if self.is_float:
            value = float(text)
        else:
            if "." in text:
                raise self.error(tokens, f"expected a whole number, got {text}")
            value = int(text, 0)

        return {self.name: -value if negative else value}

    def write(self, opcode: Opcode, decompiler: "Decompiler") -> list[Token]:
        value = getattr(opcode, self.name)
        text = float_text(float(value)) if self.is_float else str(int(value))

        return [synth_token("NUMBER", text)]


def read_arguments(
    arguments: list[list[Token]],
    spec: list[Argument],
    opcode: Opcode,
    compiler: "Compiler",
) -> None:
    """Read each argument into `opcode`'s fields, filling in the ones that were
    left out with their defaults."""
    for index, argument in enumerate(spec):
        if index < len(arguments):
            fields = argument.read(arguments[index], compiler)
        else:
            fields = argument.absent()

        for name, value in fields.items():
            setattr(opcode, name, value)


def write_arguments(
    spec: list[Argument], opcode: Opcode, decompiler: "Decompiler"
) -> list[list[Token]]:
    """Write `opcode`'s fields back out, stopping at the first optional
    argument that is not there -- nothing after it can be written either."""
    out: list[list[Token]] = []

    for argument in spec:
        if argument.optional and not argument.present(opcode):
            break

        out.append(argument.write(opcode, decompiler))

    for argument in spec[len(out) :]:
        if not argument.optional:
            raise DecompileError(
                f"`{argument.name}` is not optional but comes after an argument "
                + "that is missing, so this opcode cannot be written out"
            )

    return out


