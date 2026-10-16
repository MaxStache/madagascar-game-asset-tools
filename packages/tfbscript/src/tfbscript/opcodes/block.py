"""Shared base for the four 0xFF control blocks that partition a script.

They carry no payload; which block an 0xFF opcode is depends only on how many
0xFF opcodes came before it (see ParserContext.control_block_counter).
"""

from dataclasses import dataclass
from typing import override

from tfbscript.opcodes.base import Opcode
from tfbscript.payload import PayloadReader


@dataclass
class BlockOpcode(Opcode):
    """A named top-level block: prints as `[ NAME ]` ... `[ NAME: END ]`."""

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "BlockOpcode":
        return cls()

    def block_name(self) -> str:
        raise NotImplementedError

    @override
    def source_line(self, inline: bool = False) -> str:
        return f"[ {self.block_name()} ]"

    @override
    def print_tree(self, indent: int = 0) -> None:
        print()
        super().print_tree(indent)
        print(f"{'    ' * indent}[ {self.block_name()}: END ]\n")
