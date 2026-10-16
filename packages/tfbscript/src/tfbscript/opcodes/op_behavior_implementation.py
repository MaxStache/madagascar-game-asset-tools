from dataclasses import dataclass
from typing import Any, BinaryIO, override

from tfbscript.opcodes.block import BlockOpcode
from tfbscript.string_table import StringTableEntry


@dataclass
class OpBehaviorImplementation(BlockOpcode):
    # The behavior's entry in the local ref table, resolved by Opcode.read;
    # used for printing.
    behavior_entry: StringTableEntry | None = None

    @override
    def block_name(self) -> str:
        name = self.behavior_entry.name if self.behavior_entry else "ERR Failed to resolve"
        return f"Behavior {name}"

    @override
    def source_line(self, inline: bool = False) -> str:
        name = self.behavior_entry.name if self.behavior_entry else "ERR Failed to resolve"
        return f"[ Behavior: {name} ]"

    @override
    def editor_repr(self) -> dict[str, Any]:
        name = self.behavior_entry.name if self.behavior_entry else "ERR Failed to resolve"

        return {
            "fields": [
                {
                    "type": "behavior-label",
                    "value": name,
                }
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        pass # Behavior implementation has no payload