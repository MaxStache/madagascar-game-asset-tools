from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import method, parentheses
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import MembershipCombiner
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("change membership")
@dataclass
class OpChangeMembership(Opcode):
    ref: Reference = field(default_factory=Reference)
    membershipCombiner: MembershipCombiner = field(default=MembershipCombiner.add)
    ref2: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpChangeMembership":
        ref = reader.readRef()
        membershipCombiner = MembershipCombiner(reader.read_u8())
        ref2 = reader.readRef()
        return cls(ref=ref, membershipCombiner=membershipCombiner, ref2=ref2)

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{self.ref}.{method(self.membershipCombiner.symbol())}{parentheses('(')}{self.ref2}{parentheses(')')};"

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.ref.write(f)
        write_u8(f, self.membershipCombiner)
        self.ref2.write(f)

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "set [set]",
                },
                {
                    "type": "ref",
                    "ref": self.ref,
                },
                {
                    "type": "label",
                    "content": "to",
                },
                {
                    "type": "enum",
                    "value": self.membershipCombiner,
                },
                {
                    "type": "ref",
                    "ref": self.ref2,
                },
            ]
        }
