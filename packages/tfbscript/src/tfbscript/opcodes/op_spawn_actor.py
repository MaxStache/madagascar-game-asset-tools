from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import keyword
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs

# TODO: RESEARCH REMAINING BYTE PURPOSE


@opcode("spawn actor")
@dataclass
class OpSpawnActor(Opcode):
    clone_ref: Reference = field(default_factory=Reference)
    at_ref: Reference = field(default_factory=Reference)
    facing_rhs: Rhs = field(default_factory=Rhs)
    remaining: int | None = None

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpSpawnActor":
        clone_ref = reader.readRef()
        at_ref = reader.readRef()
        facing_rhs = reader.readRHS()

        if reader.size_remaining() > 0:
            return cls(
                clone_ref=clone_ref,
                at_ref=at_ref,
                facing_rhs=facing_rhs,
                remaining=reader.read_u8(),
            )
        return cls(clone_ref=clone_ref, at_ref=at_ref, facing_rhs=facing_rhs)


    @override
    def source_line(self, inline: bool = False) -> str:
        if self.remaining is not None:
            return f"{keyword(f'spawn actor ({self.clone_ref}, at: {self.at_ref}, facing: {self.facing_rhs}, unknown: {self.remaining})')};"
        else:
            return f"{keyword(f'spawn actor ({self.clone_ref}, at: {self.at_ref}, facing: {self.facing_rhs})')};"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "clone",
                },
                {
                    "type": "label",
                    "content": "actor",
                },
                {
                    "type": "ref",
                    "name": "clone_ref",
                    "ref": self.clone_ref,
                },
                {
                    "type": "label",
                    "content": "at",
                },
                {
                    "type": "ref",
                    "name": "at_ref",
                    "ref": self.at_ref,
                },
                {
                    "type": "label",
                    "content": "facing",
                },
                {
                    "type": "rhs",
                    "name": "facing_rhs",
                    "rhs": self.facing_rhs,
                },
                {
                    "type": "label",
                    "content": "degrees",
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.clone_ref.write(f)
        self.at_ref.write(f)
        self.facing_rhs.write(f)
        # The trailing byte is only there in some files; parse records its
        # absence as None so writing can leave it out again.
        if self.remaining is not None:
            write_u8(f, self.remaining)
