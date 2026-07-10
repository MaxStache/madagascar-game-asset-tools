import io
from dataclasses import dataclass, field

from ...lib.parser import Parser
from ...rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_TFB_UNKNOWN3(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_TFB_UNKNOWN3":
        unk2= RW_TFB_UNKNOWN3()
        unk2.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            unk2.header,
            0x800000f6,
            "RW_TFB_UNKNOWN3 chunk type",
        )

        #print(f"RW_TFB_UNKNOWN3: {unk2.header}")
        #print(f"    : {parser.readBytes(unk2.header.size).hex()}")

        return unk2

    def write(this, f, stamp):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=0x800000f6,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())