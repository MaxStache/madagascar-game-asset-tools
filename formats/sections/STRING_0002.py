from ..lib.utils import bytes_pad4
from ..rwConstants import RWSectionType
from ..lib.parser import Parser
from ..rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise
from dataclasses import dataclass, field
import io

@dataclass
class RW_String(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    content: str = ""  # header.payload_size

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_String":
        string = RW_String()

        string.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            string.header,
            RWSectionType.rwID_STRING.value,
            "RW_String chunk type",
        )

        string.content = parser.readBytes(
            string.header.size
        ).decode("latin-1", errors="replace")
      
        return string

    def write(this, f, stamp):
        buf = io.BytesIO()

        enc_string = bytes_pad4(
            this.content.encode("latin-1", errors="replace")
        )
        buf.write(enc_string)
    
        rw_header = RWHeader(
            type=RWSectionType.rwID_STRING.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())