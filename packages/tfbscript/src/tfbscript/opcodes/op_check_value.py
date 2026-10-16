from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import comparison, keyword
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import RelOp
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("check value")
@dataclass
class OpCheckValue(Opcode):
    lhs: Reference = field(default_factory=Reference)
    rel_op: RelOp = RelOp.Eq
    rhs: Rhs = field(default_factory=Rhs)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpCheckValue":
        lhs = reader.readRef()
        rel_op = RelOp(reader.read_u8())
        rhs = reader.readRHS()
        return cls(lhs=lhs, rel_op=rel_op, rhs=rhs)

    @override
    def source_line(self, inline: bool = False) -> str:
        condition = f"{self.lhs} {comparison(self.rel_op.symbol())} {self.rhs}"
        if inline:
            return condition

        return f"{keyword('check value (')} {condition} {keyword(')')}"


    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "hasBody": True,
            "fields": [
                {
                    "type": "op-label",
                    "value": "check value",
                },
                {
                    "type": "ref",
                    "ref": self.lhs,
                },
                {
                    "type": "enum",
                    "name": "rel_op",
                    "entry": self.rel_op,
                },
                {
                    "type": "rhs",
                    "rhs": self.rhs,
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.lhs.write(f)
        write_u8(f, self.rel_op.value)
        self.rhs.write(f)