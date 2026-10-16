from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from tfbscript.ansi import func_call
from tfbscript.binary import write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import CutsceneCommand
from tfbscript.payload import PayloadReader

@opcode("cut-scene")
@dataclass
class OpCutScene(Opcode):
    cutscene_command: CutsceneCommand = field(default=CutsceneCommand.Begin)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpCutScene":
        cutscene_cmd = CutsceneCommand(reader.read_u8())
        return cls(cutscene_command=cutscene_cmd)

    @override
    def source_line(self, inline: bool = False) -> str:
        return func_call("cutScene", str(self.cutscene_command))

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "hasBody": False,
            "fields": [
                {
                    "type": "op-label",
                    "value": "cut-scene",
                },
                {
                    "type": "enum",
                    "name": "cutscene_command",
                    "entry": self.cutscene_command,
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        write_u8(f, self.cutscene_command)