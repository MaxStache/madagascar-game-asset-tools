from dataclasses import dataclass
from typing import Any, BinaryIO, override

from tfbscript.ansi import comment
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader


@opcode("comment:")
@dataclass
class OpComment(Opcode):
    content: str = ""

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpComment":
        content = reader.read_string(reader.read_u8())
        return cls(content=content)

    @override
    def source_line(self, inline: bool = False) -> str:
        return comment(f"// {self.content}")

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "label",
                    "content": "comment:",
                },
                {
                    "type": "string",
                    "value": self.content,
                },
            ]
        }
    
    @override
    def write_payload(self, f: BinaryIO) -> None:
        write_u8(f, len(self.content))
        f.write(self.content.encode("latin1"))