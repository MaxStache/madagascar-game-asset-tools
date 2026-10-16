from dataclasses import dataclass, field
from typing import BinaryIO, override

from tfbscript.ansi import method, parentheses
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("stop sound")
@dataclass
class OpStopSound(Opcode):
    sound: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpStopSound":
        return cls(sound=reader.readRef())

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.sound.write(f)
        
    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{self.sound}.{method('stop')}{parentheses('()')};"
