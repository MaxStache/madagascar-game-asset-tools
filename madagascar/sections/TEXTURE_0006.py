import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from madagascar.lib.parser import Parser
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.writer import write_u8, write_u16
from madagascar.sections.EXTENSION_0003 import RW_Extension
from madagascar.sections.STRING_0002 import RW_String


@dataclass
class RW_Texture_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    filterMode: int = 0  # u8
    addressModes: int = 0  # u8
    useMipLevels: bool = False  # u16

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Texture_Struct":
        texture_s = cls()
        texture_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texture_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_Texture_Struct chunk type",
        )

        texture_s.filterMode = parser.readUint8()
        texture_s.addressModes = parser.readUint8()
        texture_s.useMipLevels = bool(parser.readUint16())

        return texture_s

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u8(buf, self.filterMode)
        write_u8(buf, self.addressModes)
        write_u16(buf, self.useMipLevels)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_Texture(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_Texture_Struct = field(default_factory=RW_Texture_Struct)

    diffuseTextureName: RW_String = field(default_factory=RW_String)

    alphaTextureName: RW_String = field(default_factory=RW_String)

    extension: RW_Extension = field(default_factory=RW_Extension)

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Texture":
        texture = cls()
        texture.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texture.header,
            RWSectionType.rwID_TEXTURE.value,
            "RW_Texture chunk type",
        )

        texture.struct = RW_Texture_Struct.read(parser)

        texture.diffuseTextureName = RW_String.read(parser)

        texture.alphaTextureName = RW_String.read(parser)

        texture.extension = RW_Extension.read(parser, parent=texture)

        return texture
    
    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        self.struct.write(buf, stamp)

        self.diffuseTextureName.write(buf, stamp, parent=self)

        self.alphaTextureName.write(buf, stamp, parent=self)

        self.extension.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_TEXTURE.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
