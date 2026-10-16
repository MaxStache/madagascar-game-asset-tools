from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import method, parentheses
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("remove")
@dataclass
class OpRemove(Opcode):
    target: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpRemove":
        return cls(target=reader.readRef())

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{self.target}.{method('remove')}{parentheses('()')};"


    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "hasBody": False,
            "fields": [
                {
                    "type": "op-label",
                    "value": "remove",
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