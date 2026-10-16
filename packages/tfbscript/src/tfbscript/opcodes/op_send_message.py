from dataclasses import dataclass, field
from typing import BinaryIO, override

from tfbscript.ansi import func_call
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs


@opcode("send message")
@dataclass
class OpSendMessage(Opcode):
    message_ref: Reference = field(default_factory=Reference)
    reciver_Ref: Reference = field(default_factory=Reference)
    value: Rhs = field(default_factory=Rhs)
    # The byte at payload+8 is the RHS record's own rec+8 field -- the same one
    # `check message` reads as its relational operator (both opcodes hand it to
    # FUN_0042FC60 before readRHS). Send's execute never looks at it, but it is
    # not always zero on disk ({0: 20, 2: 636} across the corpus), so it is kept
    # verbatim rather than assumed.
    _rec8: int = 0

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpSendMessage":
        message_ref = reader.readRef()
        reciver_ref = reader.readRef()
        rec8 = reader.read_u8()
        value = reader.readRHS()
        return cls(
            message_ref=message_ref,
            reciver_Ref=reciver_ref,
            value=value,
            _rec8=rec8,
        )

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.message_ref.write(f)
        self.reciver_Ref.write(f)
        write_u8(f, self._rec8)
        self.value.write(f)

    @override
    def source_line(self, inline: bool = False) -> str:
        return func_call(
            "sendMessage",
            str(self.message_ref),
            f"to: {self.reciver_Ref}",
            f"value: {self.value}",
        )
