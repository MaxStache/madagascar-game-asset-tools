import struct
from dataclasses import dataclass
from typing import Optional

from formats.lib.parser import Parser
from formats.lib.sytax_hilighting import Color, color_text, text_rgb_square
from formats.lib.tfb_reference import parse_reference


@dataclass
class RHSValue:
    tag: int
    kind: str
    value: object
    operator: Optional[int] = None
    rhs: Optional["RHSValue"] = None


def read_rhs(
    parser: Parser,
    table2: Optional[list] = None,
    table3: Optional[list] = None,
) -> RHSValue:
    """
    Reads a Set Value RHS expression.
    """

    # A reference is 5 bytes (tag + 4-byte ref) unless there's room left for
    # the 6-byte "op + value2" tail (11 bytes total). This must be decided
    # from how many bytes are actually left in the payload -- peeking at the
    # next byte and guessing "tail present unless it's 0xFF" is wrong: that
    # byte can legitimately be anything (e.g. 0x00), and misreading it as a
    # tail marker walks straight past the end of the buffer.
    avail = parser.remaining()
    tag = parser.readUint8()

    # ------------------------------------------------------------------
    # Reference
    # ------------------------------------------------------------------
    if tag == 0x02:
        ref = parse_reference(parser.readBytes(4), table2=table2, table3=table3)

        if avail < 11:
            return RHSValue(tag, "reference", ref)

        op = parser.readUint8()
        rhs = read_rhs(parser, table2, table3)

        return RHSValue(
            tag=tag,
            kind="expression",
            value=ref,
            operator=op,
            rhs=rhs,
        )

    # ------------------------------------------------------------------
    # Integer
    # ------------------------------------------------------------------
    if (tag & 0xF0) == 0x00:
        value = struct.unpack("<i", parser.readBytes(4))[0]
        return RHSValue(tag, "int", value)

    # ------------------------------------------------------------------
    # Float -- the low nibble is a subtype variant (0x10, 0x11, ... all seen
    # in shipped scripts), not part of the kind selector; only the high
    # nibble picks the kind, same as the int/color/pair checks below.
    # ------------------------------------------------------------------
    if (tag & 0xF0) in (0x10, 0x80):
        value = struct.unpack("<f", parser.readBytes(4))[0]
        value = round(value, 7)  # round to 7 decimal places for display
        return RHSValue(tag, "float", value)

    # ------------------------------------------------------------------
    # RGBA color
    # ------------------------------------------------------------------
    if (tag & 0xF0) == 0x20:
        value = tuple(parser.readBytes(4))
        return RHSValue(tag, "color", value)

    # ------------------------------------------------------------------
    # int16 pair
    # ------------------------------------------------------------------
    if (tag & 0xF0) == 0x30:
        value = struct.unpack("<hh", parser.readBytes(4))
        return RHSValue(tag, "pair", value)

    raise ValueError(f"Unknown RHS tag 0x{tag:02X}")


def rhs_to_string(rhs: RHSValue, enable_coloring: bool = True, filterPlusMinusZero: bool = False, showTypes: bool = True) -> str:
    """
    Converts an RHSValue into a readable string representation.
    """

    if rhs.kind == "int":
        if showTypes:
            text = f"Int32: {rhs.value}"
        else:
            text = f"{rhs.value}"

        return (
            color_text(text, Color.NUMBER)
            if enable_coloring
            else text
        )

    if rhs.kind == "float":
        if showTypes:
            text = f"Float: {rhs.value}"
        else:
            text = f"{rhs.value}"

        return (
            color_text(text, Color.NUMBER)
            if enable_coloring
            else text
        )

    if rhs.kind == "color":
        r, g, b, a = rhs.value

        if showTypes:
            text = f"Color32: ({r}, {g}, {b}, {a})"
        else:
            text = f"Color({r}, {g}, {b}, {a})"

        if enable_coloring:
            return text_rgb_square(r, g, b) + color_text(
                text,
                Color.RGBACOLOR,
            )
        else:
            return text

    if rhs.kind == "pair":
        # two little-endian half floats
        x, y = rhs.value
        return (
            color_text(f"Pair16: ({x}, {y})", Color.NUMBER)
            if enable_coloring
            else f"Pair16: ({x}, {y})"
        )

    if rhs.kind == "reference":
        if showTypes:
            text = f"Ref: {rhs.value}"
        else:
            text = f"{rhs.value}"

        return (
            color_text(text, Color.REFERENCE)
            if enable_coloring
            else text
        )

    if rhs.kind == "expression":
        operators = {
            0: "+",
            1: "-",
            2: "*",
            3: "/",
        }

        op = operators.get(rhs.operator, f"unknown_operator_{rhs.operator}")

        left = (
            color_text(f"Ref: {rhs.value}", Color.REFERENCE)
            if enable_coloring
            else f"Ref: {rhs.value}" if showTypes else f"{rhs.value}"
        )

        if filterPlusMinusZero and rhs.rhs.kind == "int" and rhs.rhs.value == 0 and rhs.operator in (0, 1):
            # if filterPlusMinusZero and rhs is int and rhs.value is 0 and operator is + or -, then return just the left side
            return f"({left})"

        operator_str = color_text(op, Color.OPERATOR) if enable_coloring else str(op)

        right = rhs_to_string(rhs.rhs, enable_coloring, filterPlusMinusZero, showTypes)


        return f"({left} {operator_str} {right})"

    return f"Unknown({rhs.kind}): {rhs.value}"
