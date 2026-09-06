import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from madagascar.lib.parser import Parser
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise
from madagascar.lib.writer import write_u32
       

@dataclass
class RW_TFB_TFBTextureExt1(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    version: int = field(default=0xf0f0f04)

    unknown1: int = field(default=0x00)
    unknown2: int = field(default=0x00)


    @classmethod
    @override
    def read(
        cls, parser: Parser, parent: RW_Section | None = None
    ) -> "RW_TFB_TFBTextureExt1":
        tfbtexture1 = cls()
        tfbtexture1.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            tfbtexture1.header,
            0x800000DD,
            "RW_TFB_TFBTextureExt1 chunk type",
        )

        tfbtexture1.version = parser.readUint32()

        tfbtexture1.unknown1 = parser.readUint32()
        tfbtexture1.unknown2 = parser.readUint32()
       
        return tfbtexture1

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u32(buf, self.version)
        write_u32(buf, self.unknown1)
        write_u32(buf, self.unknown2)

        rw_header = RWHeader(
            type=0x800000DD,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
