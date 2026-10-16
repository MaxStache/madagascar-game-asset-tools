from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import keyword
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import ControlRequirement
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("control")
@dataclass
class OpControl(Opcode):
    target: Reference = field(default_factory=Reference)
    script_control: ControlRequirement = field(default=ControlRequirement.Allow)

    # Whether the payload carries the script_control byte. The byte is there
    # for an actor target, but the target's type is the wrong thing to ask:
    # resolving it only works while the read traversal is still inside the
    # enclosing ops (see ParserContext.open_opcodes), so writing -- which
    # happens outside any traversal -- got a different answer and dropped the
    # byte. The payload length says it outright, there being only two shapes,
    # 4 bytes for the reference alone and 5 with the byte. Measured over the
    # corpus: 12,376 control ops, 965 of them 4 bytes and 11,411 of them 5,
    # nothing else -- and the type test disagreed with the bytes 72 times.
    _has_script_control: bool = True

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpControl":
        target = reader.readRef()

        script_control = ControlRequirement.Allow
        has_script_control = reader.size_remaining() >= 1

        if has_script_control:
            script_control = ControlRequirement(reader.read_u8())

        return cls(
            target=target,
            script_control=script_control,
            _has_script_control=has_script_control,
        )

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"{keyword('control (')} {self.target}, {self.script_control} {keyword(')')}"

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.target.write(f)
        if self._has_script_control:
            write_u8(f, self.script_control)

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "hasBody": True,
            "fields": [
                {
                    "type": "op-label",
                    "value": "control",
                },
                {
                    "type": "ref",
                    "name": "target",
                    "ref": self.target,
                },
                {
                    "type": "op-label",
                    "value": "script control: ",
                },
                {
                    "type": "enum",
                    "name": "script_control",
                    "entry": self.script_control,
                },
            ],
        }
