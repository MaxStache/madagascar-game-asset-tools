from dataclasses import dataclass
from typing import Any, BinaryIO, override

from tfbscript.opcodes.block import BlockOpcode


@dataclass
class OpShutdown(BlockOpcode):
    @override
    def block_name(self) -> str:
        return "SHUTDOWN"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "block-label",
                    "value": "SHUTDOWN",
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        pass # Shutdown has no payload