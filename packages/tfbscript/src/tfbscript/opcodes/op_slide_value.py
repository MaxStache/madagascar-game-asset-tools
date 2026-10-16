from dataclasses import dataclass, field
from typing import override

from typing import BinaryIO

from tfbscript.ansi import func_call
from tfbscript.binary import write_u32
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("slide value")
@dataclass
class OpSlideValue(Opcode):
    lhs: Reference = field(default_factory=Reference)
    target_value: Rhs = field(default_factory=Rhs)
    interpolation_time: Rhs = field(default_factory=Rhs)

    # Plain u32s, not references: slide value's parse (FUN_00430210) reads
    # them with FUN_00432990 -- a thunk to FUN_00432920, a raw 4-byte LE read --
    # not with FUN_004346f0, which is what every actual reference operand goes
    # through. Disk order is ease_out (obj+0x28) then ease_in (obj+0x24).
    ease_out: int = 0
    ease_in: int = 0
    # Whatever is left when the trailer is not the expected 8 bytes. That only
    # happens when the RHS reader took an operator tail that was not really
    # there (see Rhs._tail_follows -- the byte test is sound but not complete),
    # so the fields above are unreliable for those; keeping the raw bytes lets
    # the file round-trip exactly regardless.
    _trailing: bytes = b""

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> Opcode:
        lhs = reader.readRef()
        target_value = reader.readRHS()
        interpolation_time = reader.readRHS()

        # Normally exactly 8 bytes remain.
        if reader.size_remaining() >= 8:
            return cls(
                lhs=lhs,
                target_value=target_value,
                interpolation_time=interpolation_time,
                ease_out=reader.read_u32(),
                ease_in=reader.read_u32(),
            )

        return cls(
            lhs=lhs,
            target_value=target_value,
            interpolation_time=interpolation_time,
            _trailing=reader.read_bytes(reader.size_remaining()),
        )

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.lhs.write(f)
        self.target_value.write(f)
        self.interpolation_time.write(f)
        if self._trailing:
            f.write(self._trailing)
        else:
            write_u32(f, self.ease_out)
            write_u32(f, self.ease_in)

    @override
    def source_line(self, inline: bool = False) -> str:
        return (
            str(self.lhs)
            + "."
            + func_call(
                "slide",
                f"to {self.target_value!s}",
                f"over {self.interpolation_time!s}",
                f"ease in {self.ease_out!s}",
                f"ease out {self.ease_in!s}",
            )
        )
