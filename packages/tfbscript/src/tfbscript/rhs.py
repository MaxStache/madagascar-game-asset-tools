"""The 5-11 byte right-hand-side operand used by value opcodes."""

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, BinaryIO, cast, override

from tfbscript.ansi import number, operator, rgb_square, type_
from tfbscript.binary import write_f32, write_i16, write_rgba, write_s32, write_u8
from tfbscript.reference import Reference
from tfbscript.string_table import StringTable

if TYPE_CHECKING:
    from tfbscript.binary import BinaryReader
    from tfbscript.opcodes.base import ParserContext

_OPERATORS = {
    0x00: "+",
    0x01: "-",
    0x02: "*",
    0x03: "/",
}

class RhsKind(IntEnum):
    ADWAD = 234
@dataclass
class Rhs:
    tag: int = 0x00
    kind: str = (
        "null"  # 'int' | 'float' | 'color' | 'pair' | 'reference' | 'expression'
    )
    value: object = None
    operator: int | None = None
    rhs: "Rhs | None" = None

    @property
    def is_random(self) -> bool:
        """Whether this immediate is a random ceiling (low-nibble bit 0).

        Only meaningful for int/float kinds: tags 0x01 / 0x11 mean the engine
        produces a uniform random value in [0, value) at runtime instead of
        using the literal verbatim.
        """
        return self.kind in ("int", "float") and bool(self.tag & 0x01)

    @classmethod
    def read(
        cls,
        reader: "BinaryReader",
        global_refs: StringTable,
        local_refs: StringTable,
        context: "ParserContext | None" = None,
    ) -> "Rhs":
        """Parse a 5-11 byte TFB-Script RHS.

        Args:
            reader: BinaryReader positioned at the RHS.
            global_refs: the script's 2nd string table (globals) for name resolution.
            local_refs: the script's 3rd string table (locals) for name resolution.
            context: the script's parser context, threaded through to any
                embedded References so they can resolve builtin types.
        Returns:
            An Rhs.
        """

        # A reference is 5 bytes (tag + 4-byte ref) unless there's room left for
        # the 6-byte "op + value2" tail (11 bytes total), decided here from how
        # many bytes are left in the payload.
        #
        # This is a proxy, not what the engine does. The real reader is
        # TFBScript::readRHS @ 0043fd20 (4 stack args, RET 0x10; arg1 = the
        # record, arg2 = a "gate" object, arg3 = a flag, arg4 unused). Its only
        # tail branch is:
        #
        #   0043fd59  CMP byte [EDI],2      ; tag A, from the stream
        #   0043fd63  JNZ 0043fe3e          ; constant -> no tail
        #   0043fd69  TEST EBP,EBP          ; EBP = arg2, the gate
        #   0043fd6b  JZ  0043fd82          ; gate NULL -> tail
        #   0043fd6d  CALL 0042fdb0         ; the `value` exemplar
        #   0043fd75  CALL 0043bab0         ; is-a(gate, value); `set` counts as value
        #   0043fd7c  JZ  0043fe3e          ; not is-a value -> NO tail (5 bytes)
        #   0043fd82  ...                   ; tail: op + tag B + term B (11 bytes)
        #
        # Call sites pass as the gate either DAT_0061f870 -- the descriptor
        # FUN_004346f0 left from the last reference read in the same parse
        # (set value 0042fb82, check value, check message 0043aecf, send
        # message 0043af7f) -- or a fixed exemplar (`angle` at 00431457 /
        # 00435a3f / 00435a56, `value` at 00435a99) or NULL (00430284).
        #
        # NOT YET REPRODUCIBLE STATICALLY. The outcome *is* static: keyed by
        # (script, LHS operand word) there are 0 conflicts in 5165 pairs. But
        # it is not a function of the gate's type as modelled here -- restricted
        # to set value, whose gate is provably the LHS, the same actor field
        # descriptor yields both sizes across files (waypoints 555/75,
        # heading (OBSOLETE) 9/61, origin 11/5, tint color 6/5). Field-class
        # identity does not separate them either: the 56 ::actor field
        # descriptors (array 0x0061fdc0, builder FUN_00436f80) fall into just 6
        # getClass groups -- 42fdb0 `value` (42 fields), 43d2d0 `set`
        # (waypoints/attach points/clones/turrets), 4302c0 `angle`
        # (heading/facing/cone angle/cone sweep offset), 42fdf0 colour
        # (blip/cone/tint color), 430300 point (origin/destination), 42fe70
        # (current speed) -- and every one of those groups shows both sizes.
        # So DAT_0061f870 at the call must not always be the last-read
        # reference; that is the open thread.
        #
        # Meanwhile the length proxy holds: the authoring tool sized
        # payload_size to whatever it emitted, so the remaining-bytes boundary
        # reproduces the decision. Verified across the corpus (0 parse errors,
        # and every round-trip mismatch attributable to opcodes with no
        # write_payload).

        available = reader.size_remaining()
        tag = reader.read_u8()

        # Reference, optionally extended to an expression by an operator tail.
        if tag == 0x02:
            ref = Reference.read(reader, global_refs, local_refs, context)

            if available < 11 or not cls._tail_follows(reader):
                return cls(tag, "reference", ref)

            op = reader.read_u8()
            # The tail's second operand is a plain TERM, never another
            # expression: Game.exe's readRHS reads it with a single
            # FUN_004346f0 (reference, 0043fe27) or one constant reader, and
            # there is no operator after it. Recursing into Rhs.read here would
            # eat the following field whenever term B is itself a reference --
            # e.g. slide value `.. 02 refA 00 02 refB | 10 cd cc cc 3e ..`,
            # where the 0x10 float tag gets misread as an operator and 0xCD (the
            # mantissa of 0.4f) as a tag.
            rhs = cls._read_term(reader, global_refs, local_refs, context)
            return cls(tag, "expression", ref, operator=op, rhs=rhs)

        return cls._read_term_body(reader, tag, global_refs, local_refs, context)

    @staticmethod
    def _tail_follows(reader: "BinaryReader") -> bool:
        """Whether an operator + second term really follows the reference just read.

        The remaining-bytes test alone is not enough: an opcode that has more
        fields after its RHS leaves plenty of room even when there is no tail,
        and the reader then eats the next field. Game.exe decides this by type
        (readRHS @ 0043fd20 takes the tail only when its gate argument is-a
        `value`), which a static decoder cannot reproduce -- but the bytes a
        real tail must have are tightly constrained, and that is checkable:

        * the operator at rec+0xb is a 2-bit selector, 0 `+` / 1 `-` / 2 `*` /
          3 `/`. The evaluator (FUN_004400C0 @ 0044022C and 004402FE) does
          `CMP EAX,3; JA` and falls through doing nothing above 3, so a byte
          > 3 is not an operator;
        * the second term's tag is one the reader dispatches on -- exactly
          0x02, or a high nibble of 0x00/0x10/0x20/0x30/0x80.

        Measured over the corpus: 40,543 tails, operator 0-3 in every genuine
        one; the only 7 exceptions had 0x10 there -- a float tag from the
        *following* field, i.e. precisely the over-read this rejects.
        """
        if reader.size_remaining() < 6:
            return False

        op = reader.data[reader.offset]
        tag_b = reader.data[reader.offset + 1]

        if op > 0x03:
            return False
        if tag_b == 0x02:
            return True
        return (tag_b & 0xF0) in (0x00, 0x10, 0x20, 0x30, 0x80)

    @classmethod
    def _read_term(
        cls,
        reader: "BinaryReader",
        global_refs: StringTable,
        local_refs: StringTable,
        context: "ParserContext | None" = None,
    ) -> "Rhs":
        """Read one operand of an expression: a tag plus its value, with no
        operator tail. Used for the second operand only."""
        tag = reader.read_u8()

        if tag == 0x02:
            ref = Reference.read(reader, global_refs, local_refs, context)
            return cls(tag, "reference", ref)

        return cls._read_term_body(reader, tag, global_refs, local_refs, context)

    @classmethod
    def _read_term_body(
        cls,
        reader: "BinaryReader",
        tag: int,
        global_refs: StringTable,
        local_refs: StringTable,
        context: "ParserContext | None" = None,
    ) -> "Rhs":
        """Read the value bytes of a non-reference term, given its tag."""

        if tag & 0x01 not in (0x00, 0x01):
            raise ValueError(f"Unknown RHS tag 0x{tag:02X} (low nibble {tag & 0x0F} <- CAUSE)")

        # The high nibble selects the kind (int/float/color/pair); the low
        # nibble is a "randomize" modifier -- bit 0 only. Confirmed from the
        # runtime operand evaluators (Game.exe FUN_004400c0 / FUN_00440570),
        # which switch on the exact tag byte:
        #   0x00 int literal      0x01 int, random ceiling
        #   0x10 float literal    0x11 float, random ceiling
        # For a random tag the engine yields a uniform value in [0, value) at
        # runtime (`rand() * value / 0x8000`). We keep the whole byte in `tag`,
        # so the modifier round-trips; see the `is_random` property below.

        # Integer
        if (tag & 0xF0) == 0x00:
            return cls(tag, "int", reader.read_i32())

        # Float (0x80 is the engine's "indirect float", normalized to 0x10 by
        # the reader; it takes the same 4-byte float payload).
        if (tag & 0xF0) in (0x10, 0x80):
            value = round(reader.read_f32(), 7)  # round for display
            return cls(tag, "float", value)

        # RGBA color
        if (tag & 0xF0) == 0x20:
            return cls(tag, "color", reader.read_rgba())

        # int16 pair
        if (tag & 0xF0) == 0x30:
            return cls(tag, "pair", (reader.read_i16(), reader.read_i16()))

        raise ValueError(f"Unknown RHS tag 0x{tag:02X}")

    def write(self, f: BinaryIO) -> None:
        write_u8(f, self.tag)

        if self.kind in ("reference", "expression"):
            cast(Reference, self.value).write(f)
            if self.kind == "expression":
                assert self.operator is not None
                write_u8(f, self.operator)
                assert self.rhs is not None
                self.rhs.write(f)
            return

        if self.kind == "int":
            write_s32(f, cast(int, self.value))
            return

        if self.kind == "float":
            write_f32(f, cast(float, self.value))
            return

        if self.kind == "color":
            write_rgba(f, cast(tuple[int, int, int, int], self.value))
            return

        if self.kind == "pair":
            x, y = cast(tuple[int, int], self.value)
            write_i16(f, x)
            write_i16(f, y)
            return

        raise ValueError(f"Unknown RHS kind {self.kind}")

    def to_string(
        self,
        show_types: bool = False,
        do_reconstructs: bool = False,
    ) -> str:
        """Render this RHS as a readable, syntax-colored string.
        do_reconstructs: If True, reconstructs the compiler's "x + 0" / "x - 0" expression to just "x"
        """

        if self.kind == "int":
            prefix = type_("Int: ") if show_types else ""
            body = number(self.value)
            # 0x01: random ceiling -> runtime value is uniform in [0, value).
            return prefix + (f"random(0, {body})" if self.is_random else body)

        if self.kind == "float":
            prefix = type_("Float: ") if show_types else ""
            body = number(self.value)
            # 0x11: random ceiling -> runtime value is uniform in [0, value).
            return prefix + (f"random(0, {body})" if self.is_random else body)

        if self.kind == "color":
            r, g, b, a = cast(tuple[int, int, int, int], self.value)
            prefix = type_("RGBA: ") if show_types else type_("Color")
            return rgb_square(r, g, b) + prefix + number(f"({r}, {g}, {b}, {a})")

        if self.kind == "pair":
            x, y = cast(tuple[int, int], self.value)
            prefix = type_("Pair16: ") if show_types else type_("Pair")
            return prefix + number(f"({x}, {y})")

        if self.kind == "reference":
            return f"Ref: {self.value}" if show_types else f"{self.value}"

        if self.kind == "expression":
            if self.operator is not None:
                op = _OPERATORS.get(self.operator, f"unknown_operator_{self.operator}")
                op = operator(op)
                if "unknown_operator_" in op: # TODO: bad way of doing it
                    print("WARN: UNKNOWN OPERATOR - " + hex(self.operator))
                    raise ValueError("WARN: UNKNOWN OPERATOR - " + hex(self.operator))
            else:
                op = "unknown_operator_None"

            left = f"Ref: {self.value}" if show_types else f"{self.value}"
            right = self.rhs.to_string(show_types) if self.rhs else "unknown_rhs_None"

            # `x + 0` / `x - 0` is the compiler's way of storing a bare
            # reference; reconstruct it back to just `x`.
            is_plus_minus_zero = (
                self.rhs is not None
                and self.rhs.kind == "int"
                and self.rhs.value == 0
                and self.operator in (0, 1)
            )
            if do_reconstructs and is_plus_minus_zero:
                return left
            return f"({left} {op} {right})"

        return f"Unknown({self.kind}): {self.value}"

    @override
    def __str__(self) -> str:
        return self.to_string()
