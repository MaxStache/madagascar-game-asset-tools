from dataclasses import dataclass, field
from typing import BinaryIO, override

from tfbscript.ansi import keyword
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.rhs import Rhs


@opcode("loop value", "Loops X amount of times, stores the current index in [^each]")
@dataclass
class OpLoopValue(Opcode):
    loop_amount: Rhs = field(default_factory=Rhs)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpLoopValue":
        return cls(
            loop_amount=reader.readRHS(),
        )

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{keyword('loop value (')} {self.loop_amount} {keyword(')')}"

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.loop_amount.write(f)
