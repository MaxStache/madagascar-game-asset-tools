import io
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise



@dataclass
class RW_sf_SetFrozenMode(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    def read(parser: Parser) -> "RW_sf_SetFrozenMode":
        frozenmode = RW_sf_SetFrozenMode()

        frozenmode.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            frozenmode.header,
            strfunc_func.sf_SetFrozenMode.value,
            "RW_sf_SetFrozenMode chunk type",
        )

        return frozenmode

    def write(this, f, stamp):
        buf = io.BytesIO()


        rw_header = RWHeader(
            type=strfunc_func.sf_SetFrozenMode.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    @property
    def streamfunc(self):
        return strfunc_func.sf_SetFrozenMode