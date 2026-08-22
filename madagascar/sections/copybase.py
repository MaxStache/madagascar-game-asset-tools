import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_SectionNameHere(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_SectionNameHere":
        namehere = cls()
        namehere.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            namehere.header,
            RWSectionType.rwID_NAOBJECT.value, # TODO: REPLACE!
            "RW_SectionNameHere chunk type",
        )

        return namehere

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=RWSectionType.rwID_NAOBJECT.value,  # TODO: REPLACE!
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())