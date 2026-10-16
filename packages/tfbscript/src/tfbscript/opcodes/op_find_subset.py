from dataclasses import dataclass, field
from typing import BinaryIO, override

from tfbscript.ansi import (
    comparison,
    func_call,
    variable,
)
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import RelOp
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("find subset")
@dataclass
class OpFindSubset(Opcode):
    """Filters a set by a condition; yields the subset of items that match."""

    set_ref: Reference = field(default_factory=Reference)
    rel_op: RelOp = RelOp.Eq
    rhs: Rhs = field(default_factory=Rhs)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpFindSubset":
        set_ref = reader.readRef()
        rel_op = RelOp(reader.read_u8())
        rhs = reader.readRHS()
        return cls(set_ref=set_ref, rel_op=rel_op, rhs=rhs)

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.set_ref.write(f)
        write_u8(f, self.rel_op)
        self.rhs.write(f)

    @override
    def source_line(self, inline: bool = False) -> str:
        # Rendered as: set.filter(val <op> rhs )
        val = variable("val")
        lambda_src = (
            f"{val} {comparison(self.rel_op.symbol())} {self.rhs}"
        )
        set_ref_str = str(self.set_ref)

        return f"{set_ref_str}.{func_call('filter', lambda_src)}"
