from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import func_call
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("set behavior")
@dataclass
class OpSetBehavior(Opcode):
    behavior: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpSetBehavior":
        return cls(behavior=reader.readRef())

    @override
    def source_line(self, inline: bool = False) -> str:
        return func_call("setBehavior", str(self.behavior))

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "set behavior",
                },
                {
                    "type": "ref",
                    "ref": self.behavior,
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.behavior.write(f)