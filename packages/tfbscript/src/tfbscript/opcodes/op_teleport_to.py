from dataclasses import dataclass, field
from typing import BinaryIO, override

from tfbscript.ansi import func_call
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import SetDirection
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("teleport to")
@dataclass
class OpTeleportTo(Opcode):
    target_ref: Reference = field(default_factory=Reference)
    set_direction: SetDirection = field(default=SetDirection.forward)
    facing: Rhs = field(default_factory=Rhs)

    duration: Rhs = field(default_factory=Rhs)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpTeleportTo":
        return cls(
            target_ref=reader.readRef(),
            set_direction=SetDirection(reader.read_u8()),
            facing=reader.readRHS(),
            duration=reader.readRHS(),
        )

    @override
    def source_line(self, inline: bool = False) -> str:
        return func_call(
            "teleportTo",
            str(self.target_ref),
            f"facing {self.facing}",
            f"direction: {self.set_direction}",
            f"over {self.duration} seconds",
        )

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.target_ref.write(f)
        write_u8(f, self.set_direction)
        self.facing.write(f)
        self.duration.write(f)
