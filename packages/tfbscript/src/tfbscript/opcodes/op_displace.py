from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import func_call
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import CombineMode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("displace")
@dataclass
class OpDisplace(Opcode):
    target: Reference = field(default_factory=Reference)
    combine_mode: CombineMode = field(default=CombineMode.relative)

    length: Rhs = field(default_factory=Rhs)
    heading: Rhs = field(default_factory=Rhs)
    pitch: Rhs = field(default_factory=Rhs)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpDisplace":
        target = reader.readRef()  # the object being displaced
        combine_mode = CombineMode(
            reader.read_u8()
        )  # TODO : May actually be a SetDirection

        length = reader.readRHS()
        heading = reader.readRHS()
        pitch = reader.readRHS()

        return cls(
            target=target,
            combine_mode=combine_mode,
            length=length,
            heading=heading,
            pitch=pitch,
        )

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.target.write(f)
        write_u8(f, self.combine_mode)
        self.length.write(f)
        self.heading.write(f)
        self.pitch.write(f)

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{self.target}." + func_call(
            "displace",
            str(self.combine_mode),
            "length: " + str(self.length),
            "heading: " + str(self.heading),
            "pitch: " + str(self.pitch),
        )

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "displace",
                },
                {
                    "type": "ref",
                    "name": "clone_ref",
                    "ref": self.target,
                },
                {
                    "type": "enum",
                    "name": "combine_mode",
                    "entry": self.combine_mode,
                },
                {
                    "type": "label",
                    "content": "LENGTH:",
                },
                {
                    "type": "rhs",
                    "name": "length",
                    "rhs": self.length,
                },
                {
                    "type": "label",
                    "content": "feet HEADING:",
                },
                {
                    "type": "rhs",
                    "name": "length",
                    "rhs": self.heading,
                },
                {
                    "type": "label",
                    "content": "degrees PITCH:",
                },
                {
                    "type": "rhs",
                    "name": "length",
                    "rhs": self.pitch,
                },
                {
                    "type": "label",
                    "content": "degrees",
                },
            ]
        }
