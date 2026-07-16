import io
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.writer import _write_u32
from formats.lib.rwConstants import MAKECHUNKID, RwVendor, strfunc_func
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_sf_NameHere(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)
    

    @staticmethod
    def read(parser: Parser) -> "RW_sf_NameHere":
        sf_NameHere = RW_sf_NameHere()
        sf_NameHere.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            sf_NameHere.header,
            MAKECHUNKID(RwVendor.CRITERIONRM, strfunc_func.sf_Reserved1.value), # TODO: REPLACE!
            "RW_sf_NameHere chunk type",
        )

        return sf_NameHere

    def write(this, f, stamp):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=MAKECHUNKID(RwVendor.CRITERIONRM, strfunc_func.sf_Reserved1.value), # TODO: REPLACE!
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())