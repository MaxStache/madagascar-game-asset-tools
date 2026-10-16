from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import func_call, method, parentheses
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import AnimationMapping
from tfbscript.payload import PayloadReader


@opcode("play animation")
@dataclass
class OpPlayAnimation(Opcode):
    animation: AnimationMapping = field(default=AnimationMapping.ambient)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpPlayAnimation":
        return cls(animation=AnimationMapping(reader.read_u8()))

    @override
    def source_line(self, inline: bool = False) -> str:
        if self.children:
            return f"when {method('playAnimation')}{parentheses('(')}{self.animation!s}{parentheses(')')} is done playing, do:"
        return func_call("playAnimation", str(self.animation))

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "hasBody": False,
            "fields": [
                {
                    "type": "op-label",
                    "value": "play animation",
                },
                {
                    "type": "enum",
                    "name": "animation",
                    "entry": self.animation,
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        write_u8(f, self.animation)