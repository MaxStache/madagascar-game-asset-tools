from dataclasses import dataclass
from typing import Any, BinaryIO, override

from tfbscript.opcodes.block import BlockOpcode


@dataclass
class OpStartup(BlockOpcode):
    @override
    def block_name(self) -> str:
        return "STARTUP"

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "block-label",
                    "value": "STRARTUP",
                },
            ]
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        pass # Startup has no payload