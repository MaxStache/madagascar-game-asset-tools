import io
from dataclasses import dataclass, field
import uuid

from formats.lib.parser import Parser
from formats.lib.writer import _write_alignedString, _write_u32
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_sf_CreateEntity(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    @staticmethod
    def read(parser: Parser) -> "RW_sf_CreateEntity":
        sf_centity = RW_sf_CreateEntity()
        sf_centity.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            sf_centity.header,
            strfunc_func.sf_CreateEntity.value,
            "RW_sf_CreateEntity chunk type",
        )

        return sf_centity

    def write(this, f, stamp):
        buf = io.BytesIO()

        rw_header = RWHeader(
            type=strfunc_func.sf_CreateEntity.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())