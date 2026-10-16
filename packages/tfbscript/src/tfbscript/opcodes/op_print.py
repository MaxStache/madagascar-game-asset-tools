from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import func_call, quoted_string
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("print")
@dataclass
class OpPrint(Opcode):
    target: Reference = field(default_factory=Reference)
    content: str = ""

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpPrint":
        target = reader.readRef()
        content = reader.read_string(reader.read_u8())
        return cls(target=target, content=content)

    @override
    def source_line(self, inline: bool = False) -> str:
        return func_call("print", str(self.target), quoted_string(self.content))

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "print",
                },
                {
                    "type": "ref",
                    "name": "target",
                    "ref": self.target,
                },
                {
                    "type": "string",
                    "name": "content",
                    "value": self.content,
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.target.write(f)
        write_u8(f, len(self.content))
        f.write(self.content.encode("latin1"))