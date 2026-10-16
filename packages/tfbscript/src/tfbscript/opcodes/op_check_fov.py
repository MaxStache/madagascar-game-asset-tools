from dataclasses import dataclass, field
from typing import BinaryIO, override

from tfbscript.ansi import comparison, keyword, number
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import CheckFOVMode, RelOp
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode(
    "check fov",
    """
        Is there an actor from target_ref within arc_width°
        of angle_base, whose distance to me satisfies
        "distance {range_relop} range",
        and if mode == consider_obstructions,
        i have a clear line of sight to them?
        """,
)
@dataclass
class OpCheckFOV(Opcode):
    angle_base: Rhs = field(default_factory=Rhs)
    arc_width: Rhs = field(default_factory=Rhs)

    target_ref: Reference = field(default_factory=Reference)

    range_relop: RelOp = RelOp.Eq
    range: Rhs = field(default_factory=Rhs)

    mode: CheckFOVMode = CheckFOVMode.ignore_obstructions

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpCheckFOV":
        angle_base = reader.readRHS()
        arc_width = reader.readRHS()

        target_ref = reader.readRef()

        range_relop = RelOp(reader.read_u8())
        range = reader.readRHS()

        checkfov_mode = CheckFOVMode(reader.read_u8())

        return cls(
            angle_base=angle_base,
            arc_width=arc_width,
            target_ref=target_ref,
            range_relop=range_relop,
            range=range,
            mode=checkfov_mode,
        )

    @override
    def source_line(self, inline: bool = False) -> str:
        condition = f"{self.target_ref} is within a {number(self.arc_width)}° cone centered on heading {number(self.angle_base)}, distance {comparison(self.range_relop.symbol())} {self.range}, {self.mode}"

        # Normally we would have a check for inline here,
        # but its nice to know that this is a FOV check

        return f"{keyword('check fov (')} {condition} {keyword(')')}"

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.angle_base.write(f)
        self.arc_width.write(f)
        self.target_ref.write(f)
        write_u8(f, self.range_relop)
        self.range.write(f)
        write_u8(f, self.mode)
