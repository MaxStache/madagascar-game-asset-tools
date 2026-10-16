from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import method, parentheses
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("reset")
@dataclass
class OpReset(Opcode):
    target: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpReset":
        return cls(target=reader.readRef())

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{self.target}.{method('reset')}{parentheses('()')};"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "hasBody": True,
            "fields": [
                {
                    "type": "op-label",
                    "value": "reset",
                },
                {
                    "type": "ref",
                    "ref": self.target,
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.target.write(f)