from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import operator
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("inc value")
@dataclass
class OpIncValue(Opcode):
    lhs: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpIncValue":
        return cls(lhs=reader.readRef())

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{self.lhs} {operator('++')};"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "hasBody": False,
            "fields": [
                {
                    "type": "op-label",
                    "value": "increment value",
                },
                {
                    "type": "ref",
                    "name": "lhs",
                    "ref": self.lhs,
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.lhs.write(f)