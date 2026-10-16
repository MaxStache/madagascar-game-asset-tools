from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import method, parentheses
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("play sound")
@dataclass
class OpPlaySound(Opcode):
    sound: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpPlaySound":
        return cls(sound=reader.readRef())

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.sound.write(f)

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{self.sound}.{method('play')}{parentheses('()')};"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "play sound",
                },
                {
                    "type": "ref",
                    "name": "sound",
                    "ref": self.sound,
                },
            ]
        }
