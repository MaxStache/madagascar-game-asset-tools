import io
from dataclasses import dataclass, field
from typing import override

from madagascar.lib.parser import Parser
from madagascar.lib.writer import write_u32
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_RightToRender(RW_Section):
    """https://gtamods.com/wiki/Right_To_Render_(RW_Section)
    """
    header: RWHeader = field(default_factory=RWHeader)

    plugin_id: int = 0 # should be a RWSectionType
    extra_data: bytes = b""

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_RightToRender":
        rtt = cls()
        rtt.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            rtt.header,
            RWSectionType.rwID_RIGHTTORENDER.value,
            "RW_RightToRender chunk type",
        )

        rtt.plugin_id = parser.readUint32()
        rtt.extra_data = parser.readBytes(4)

        return rtt

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u32(buf, self.plugin_id)
        buf.write(self.extra_data)

        rw_header = RWHeader(
            type=RWSectionType.rwID_RIGHTTORENDER.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
