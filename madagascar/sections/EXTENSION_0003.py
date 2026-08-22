import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import (
    RW_Section,
    RW_Section_NotImplemented,
    RWHeader,
    expect_chunk_type_or_raise,
)


@dataclass
class RW_Extension(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    children: list[RW_Section] = field(default_factory=list)

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Extension":
        from madagascar.sections import SECTION_REGISTRY

        ext = cls()
        ext.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            ext.header,
            RWSectionType.rwID_EXTENSION.value,
            "RW_Extension chunk type",
        )

        data = parser.readBytes(ext.header.size)

        sub_parser = Parser(data)

        while sub_parser.canRead(12):
            offset_before = sub_parser.tell()
            header = RWHeader.read(sub_parser)
            sub_parser.offset = offset_before

            child = SECTION_REGISTRY.get(header.type, RW_Section_NotImplemented)

            child_parser = Parser(
                sub_parser.readBytes(header.size + RWHeader.BYTE_SIZE)
            ) # Seperate parser for child section to avoid offset issues if child isnt consuming full section size

            child_instance = child.read(child_parser, parent)

            ext.children.append(child_instance)

        return ext

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        for child in self.children:
            child.write(buf, stamp, parent=parent)

        rw_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
