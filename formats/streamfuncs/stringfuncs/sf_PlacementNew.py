import io
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.writer import _write_alignedString, _write_u32
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_sf_PlacementNew(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)
    
    entry_count: int = 0
    entries: list[tuple[str, int]] = field(default_factory=list)  # List of (behavior, instanceCount) tuples

    @staticmethod
    def read(parser: Parser) -> "RW_sf_PlacementNew":
        sf_PlacementNew = RW_sf_PlacementNew()
        sf_PlacementNew.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            sf_PlacementNew.header,
            strfunc_func.sf_PlacementNew.value,
            "RW_sf_PlacementNew chunk type",
        )

        subparser = Parser(parser.readBytes(sf_PlacementNew.header.size), endian="little")

        sf_PlacementNew.entry_count = subparser.readUint32()

        for _ in range(sf_PlacementNew.entry_count):
            behavior = subparser.readPaddedCString()
            instance_count = subparser.readUint32()

            sf_PlacementNew.entries.append((behavior, instance_count))

        return sf_PlacementNew

    def write(this, f, stamp):
        buf = io.BytesIO()

        # Write entry count
        _write_u32(buf, len(this.entries))

        for behavior, instance_count in this.entries:
            _write_alignedString(buf, behavior, alignment=4)
            _write_u32(buf, instance_count)

        # doing that cus renderware wants it, idk
        _write_alignedString(buf, "", alignment=4)
        _write_u32(buf, 0)

        rw_header = RWHeader(
            type=strfunc_func.sf_PlacementNew.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    @property
    def streamfunc(self):
        return strfunc_func.sf_PlacementNew
