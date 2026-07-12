import io
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_SectionNameHere(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_SectionNameHere":
        namehere = RW_SectionNameHere()
        namehere.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            namehere.header,
            RWSectionType.rwID_NAOBJECT.value, # TODO: REPLACE!
            "RW_SectionNameHere chunk type",
        )

        return namehere

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=RWSectionType.rwID_NAOBJECT.value,  # TODO: REPLACE!
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())