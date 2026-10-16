from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import keyword, type_
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("create variable")
@dataclass
class OpCreateVariable(Opcode):
    variable: Reference = field(default_factory=Reference)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpCreateVariable":
        return cls(variable=reader.readRef())

    @override
    def source_line(self, inline: bool = False) -> str:
        var_type = self.variable.entry.type if self.variable.entry else "unknown"
        return f"{keyword('var')} {self.variable} : {type_(var_type)};"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "op-label",
                    "value": "create variable",
                },
                {
                    "type": "ref",
                    "ref": self.variable,
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.variable.write(f)