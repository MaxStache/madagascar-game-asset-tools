import io
from dataclasses import dataclass, field
from typing import override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_Rockstar_Frame(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    
    name: str = field(default="")

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Rockstar_Frame":
        frame = cls()
        frame.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            frame.header,
            RWSectionType.rwID_rockstar_Frame.value,
            "RW_Rockstar_Frame chunk type",
        )

        frame.name = parser.readBytes(frame.header.size).decode("latin-1")

        return frame

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        buf.write(self.name.encode("latin-1"))

        rw_header = RWHeader(
            type=RWSectionType.rwID_rockstar_Frame.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())