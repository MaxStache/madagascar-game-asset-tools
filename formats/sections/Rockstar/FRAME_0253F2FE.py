import io
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_Rockstar_Frame(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    
    name: str = field(default="")

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_Rockstar_Frame":
        frame = RW_Rockstar_Frame()
        frame.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            frame.header,
            RWSectionType.rwID_rockstar_Frame.value,
            "RW_Rockstar_Frame chunk type",
        )

        frame.name = parser.readBytes(frame.header.size).decode("latin-1")

        return frame

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        buf.write(this.name.encode("latin-1"))

        rw_header = RWHeader(
            type=RWSectionType.rwID_rockstar_Frame.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())