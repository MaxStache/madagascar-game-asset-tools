import io
from dataclasses import dataclass, field

from ..lib.parser import Parser
from ..lib.writer import _write_u32
from ..rwConstants import RWSectionType
from ..rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_RightToRender(RW_Section):
    """https://gtamods.com/wiki/Right_To_Render_(RW_Section)
    """
    header: RWHeader = field(default_factory=RWHeader)

    plugin_id: int = 0 # should be a RWSectionType
    extra_data: bytes = b""

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_RightToRender":
        rtt = RW_RightToRender()
        rtt.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            rtt.header,
            RWSectionType.rwID_RIGHTTORENDER.value,
            "RW_RightToRender chunk type",
        )

        rtt.plugin_id = parser.readUint32()
        rtt.extra_data = parser.readBytes(4)

        return rtt

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_u32(buf, this.plugin_id)
        buf.write(this.extra_data)

        rw_header = RWHeader(
            type=RWSectionType.rwID_RIGHTTORENDER.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
