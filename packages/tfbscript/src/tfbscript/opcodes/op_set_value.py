from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import keyword, operator
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("set value")
@dataclass
class OpSetValue(Opcode):
    lhs: Reference = field(default_factory=Reference)
    rhs: Rhs = field(default_factory=Rhs)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpSetValue":
        return cls(lhs=reader.readRef(), rhs=reader.readRHS())

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{keyword('set')} {self.lhs} {operator('=')} {self.rhs};"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "set value",
                },
                {
                    "type": "ref",
                    "ref": self.lhs,
                },
                {
                    "type": "label",
                    "content": "=",
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
        self.rhs.write(f)
