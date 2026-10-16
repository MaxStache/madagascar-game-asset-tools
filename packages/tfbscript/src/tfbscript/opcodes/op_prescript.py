from dataclasses import dataclass
from typing import Any, BinaryIO, override

from tfbscript.opcodes.block import BlockOpcode


@dataclass
class OpPrescript(BlockOpcode):
    @override
    def block_name(self) -> str:
        return "PRESCRIPT"

    @override
    def write_payload(self, f: BinaryIO) -> None:
        pass # Prescript has no payload

    @override
    def editor_repr(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "type": "block-label",
                    "value": "PRESCRIPT",
                },
            ]
        }