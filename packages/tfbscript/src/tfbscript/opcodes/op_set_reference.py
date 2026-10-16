from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import keyword
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("set reference")
@dataclass
class OpSetReference(Opcode):
    dest_ref: Reference = field(default_factory=Reference)
    src_ref: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpSetReference":
        return cls(dest_ref=reader.readRef(), src_ref=reader.readRef())


    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.dest_ref.write(f)
        self.src_ref.write(f)

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{keyword('set reference')} *{self.dest_ref} = {self.src_ref};"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "set *reference",
                },
                {
                    "type": "ref",
                    "ref": self.dest_ref,
                },
                {
                    "type": "label",
                    "content": "to",
                },
                {
                    "type": "ref",
                    "ref": self.src_ref,
                },
            ]
        }
