from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import keyword
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import SetDirection
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode(
    "for each",
    "Loops over a set in the order of set_direction, stores the current element in [^each]",
)
@dataclass
class OpForEach(Opcode):
    set_ref: Reference = field(default_factory=Reference)
    set_direction: SetDirection = field(default=SetDirection.forward)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpForEach":
        return cls(
            set_ref=reader.readRef(),
            set_direction=SetDirection(reader.read_u8()),
        )

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{keyword('for each [~each] in ')} {self.set_ref} {keyword('')}"

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.set_ref.write(f)
        write_u8(f, self.set_direction)

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "for each",
                },
                {
                    "type": "label",
                    "content": "in",
                },
                {
                    "type": "ref",
                    "name": "set_ref",
                    "ref": self.set_ref,
                },
                {
                    "type": "label",
                    "content": "moving",
                },
                {
                    "type": "enum",
                    "name": "set_direction",
                    "entry": self.set_direction,
                },
            ]
        }
