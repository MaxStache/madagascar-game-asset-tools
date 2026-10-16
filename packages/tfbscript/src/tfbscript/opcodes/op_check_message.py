from dataclasses import dataclass, field
from typing import BinaryIO, override

from tfbscript.ansi import keyword
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import RelOp
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("check message")
@dataclass
class OpCheckMessage(Opcode):
    message_ref: Reference = field(default_factory=Reference)

    sender_ref: Reference = field(default_factory=Reference)
    rel_op: RelOp = field(default=RelOp.Eq)
    value: Rhs = field(default_factory=Rhs)

    _is_extended: bool = field(
        default=False
    )  # has sender_ref, rel_op, value determined if payload > 4

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpCheckMessage":
        message_ref = reader.readRef()

        # Three shapes only, 4 / 14 / 20 bytes, so this threshold cannot be
        # straddled. The engine's own test is not reproducible from the .ai:
        # parse (FUN_0043AE30) asks the message's descriptor
        # DAT_0061f870->vt[0x18]() and stops right after the message ref when
        # that is <= 0 -- an operand count that comes from the message's
        # per-level declaration in the level hub, not from this file. The two
        # `message` vtables differ only there: 005CDC08 returns 0, 005CE590
        # returns 2. Verified as a per-declaration property: of 88 message
        # symbols, 79 are always extended and 8 always plain; the one that is
        # both (`ledge nearby`) is plain in 8 levels and extended in `battle`.
        #
        # Ref: 4b
        # RelOp: 1b
        # Rhs: min. 5b
        if reader.size_remaining() >= 4 + 1 + 5:
            sender_ref = reader.readRef()

            rel_op = RelOp(reader.read_u8())
            value = reader.readRHS()

            return cls(
                message_ref=message_ref,
                sender_ref=sender_ref,
                rel_op=rel_op,
                value=value,
                _is_extended=True,
            )

        return cls(
            message_ref=message_ref,
            _is_extended=False,
        )

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.message_ref.write(f)
        if not self._is_extended:
            return
        self.sender_ref.write(f)
        write_u8(f, self.rel_op)
        self.value.write(f)

    @override
    def source_line(self, inline: bool = False) -> str:
        if self._is_extended:
            condition = f"value {self.rel_op} {self.value}"
            return f"{keyword('check message (')} {self.message_ref}, sent by: {self.sender_ref}, where: {condition} {keyword(')')}"
        else:
            return f"{keyword('check message (')} {self.message_ref} {keyword(')')}"
