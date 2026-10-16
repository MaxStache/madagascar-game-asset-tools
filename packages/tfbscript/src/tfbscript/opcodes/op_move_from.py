from dataclasses import dataclass, field
from typing import BinaryIO, override

from tfbscript.ansi import func_call
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import AnimationMapping
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("move from")
@dataclass
class OpMoveFrom(Opcode):
    target_ref: Reference = field(default_factory=Reference)
    with_anim: AnimationMapping = field(default=AnimationMapping.ambient)
    until_beyond: Rhs = field(default_factory=Rhs)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpMoveFrom":
        return cls(
            target_ref=reader.readRef(),
            with_anim=AnimationMapping(reader.read_u8()),
            until_beyond=reader.readRHS(),
        )

    @override
    def source_line(self, inline: bool = False) -> str:
        base = func_call(
            "moveFrom",
            str(self.target_ref),
            f"animation: {self.with_anim}",
            f"until_beyond: {self.until_beyond}",
            add_semicolon=not self.children,
        )

        if self.children:
            return f"when {base} is done, do:"
        return base

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.target_ref.write(f)
        write_u8(f, self.with_anim)
        self.until_beyond.write(f)
