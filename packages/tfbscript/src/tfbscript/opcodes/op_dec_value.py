from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import operator
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("dec value")
@dataclass
class OpDecValue(Opcode):
    lhs: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpDecValue":
        return cls(lhs=reader.readRef())

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{self.lhs} {operator('--')};"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "hasBody": False,
            "fields": [
                {
                    "type": "op-label",
                    "value": "decrement value",
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