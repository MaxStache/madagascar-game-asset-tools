from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import func_call
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import AnimationMapping, SetDirection
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("move to")
@dataclass
class OpMoveTo(Opcode):
    target_ref: Reference = field(default_factory=Reference)
    set_direction: SetDirection = field(default=SetDirection.forward)
    with_anim: AnimationMapping = field(default=AnimationMapping.ambient)
    until_within: Rhs = field(default_factory=Rhs)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpMoveTo":
        return cls(
            target_ref=reader.readRef(),
            set_direction=SetDirection(reader.read_u8()),
            with_anim=AnimationMapping(reader.read_u8()),
            until_within=reader.readRHS(),
        )

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.target_ref.write(f)
        write_u8(f, self.set_direction)
        write_u8(f, self.with_anim)
        self.until_within.write(f)

    @override
    def source_line(self, inline: bool = False) -> str:
        base = func_call(
            "moveTo",
            str(self.target_ref),
            f"set_dir: {self.set_direction}",
            f"animation: {self.with_anim}",
            f"until_within: {self.until_within}",
            add_semicolon=not self.children,
        )

        if self.children:
            return f"when {base} is done, do:"
        return base

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "hasBody": True,
            "fields": [
                {
                    "type": "op-label",
                    "value": "move to",
                },
                {
                    "type": "ref",
                    "name": "target_ref",
                    "ref": self.target_ref,
                },
                {
                    "type": "op-label",
                    "value": "set direction: ",
                },
                {
                    "type": "enum",
                    "name": "set_direction",
                    "entry": self.set_direction,
                },
                {
                    "type": "op-label",
                    "value": "with animation: ",
                },
                {
                    "type": "enum",
                    "name": "with_anim",
                    "entry": self.with_anim,
                },
                {
                    "type": "op-label",
                    "value": "until within: ",
                },
                {
                    "type": "rhs",
                    "name": "until_within",
                    "rhs": self.until_within,
                },
                {
                    "type": "op-label",
                    "value": "ft",
                },
            ],
        }
