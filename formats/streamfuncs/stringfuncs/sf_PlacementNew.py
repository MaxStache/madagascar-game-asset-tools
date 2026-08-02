import io
from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from formats.lib.parser import Parser
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise
from formats.lib.rwConstants import strfunc_func
from formats.lib.writer import write_alignedString, write_u32


@dataclass
class RW_sf_PlacementNew(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    entry_count: int = 0
    entries: list[tuple[str, int]] = field(
        default_factory=list
    )  # List of (behavior, instanceCount) tuples

    @classmethod
    @override
    def read(cls, parser: Parser) -> "RW_sf_PlacementNew":
        sf_PlacementNew = cls()
        sf_PlacementNew.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            sf_PlacementNew.header,
            strfunc_func.sf_PlacementNew.value,
            "RW_sf_PlacementNew chunk type",
        )

        subparser = Parser(
            parser.readBytes(sf_PlacementNew.header.size), endian="little"
        )

        sf_PlacementNew.entry_count = subparser.readUint32()

        for _ in range(sf_PlacementNew.entry_count):
            behavior = subparser.readPaddedCString()
            instance_count = subparser.readUint32()

            sf_PlacementNew.entries.append((behavior, instance_count))

        return sf_PlacementNew

    @override
    def write(self, f: BinaryIO, stamp: int):
        buf = io.BytesIO()

        # Write entry count
        write_u32(buf, len(self.entries))

        for behavior, instance_count in self.entries:
            write_alignedString(buf, behavior, alignment=4)
            write_u32(buf, instance_count)

        # doing that cus renderware wants it, idk
        write_alignedString(buf, "", alignment=4)
        write_u32(buf, 0)

        rw_header = RWHeader(
            type=strfunc_func.sf_PlacementNew.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    @property
    @override
    def streamfunc(self):
        return strfunc_func.sf_PlacementNew

    @override
    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "entry_count": len(self.entries),
            "entries": [
                {"behavior": behavior, "instance_count": instance_count}
                for behavior, instance_count in self.entries
            ],
        }

    @classmethod
    @override
    def from_dict(cls, content: dict[str, Any]) -> "RW_StreamFunc":
        header = RWHeader.from_dict(content.get("header", {}))

        return cls(
            header=header,
            entry_count=len(content.get("entries",[] )),
            entries=[
                (entry.get("behavior", ""), entry.get("instance_count", 0))
                for entry in content.get("entries", [])
            ],
        )
