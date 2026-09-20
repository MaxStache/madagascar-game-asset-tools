from dataclasses import dataclass, field
from typing import override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise


@dataclass
class RWA_Stream_Data(RW_Section):
    """rwaID_STREAM_DATA (0x80F) -- every segment's samples, back to back.

    The chunk body is one opaque blob; which bytes belong to which segment and
    layer is described entirely by the 0x80E header chunk.
    """

    header: RWHeader = field(default_factory=RWHeader)

    data: bytes = b""

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RWA_Stream_Data":
        stream_data = cls()
        stream_data.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            stream_data.header,
            RWSectionType.rwaID_STREAM_DATA.value,
            "RWA_Stream_Data chunk type",
        )

        stream_data.data = parser.readBytes(stream_data.header.size)

        return stream_data

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        # The chunk body is the sample data verbatim -- no struct, no padding.
        rw_header = RWHeader(
            type=RWSectionType.rwaID_STREAM_DATA.value,
            size=len(self.data),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(self.data)

    @override
    def __repr__(self):
        return f"RWA_Stream_Data({len(self.data)} bytes)"
