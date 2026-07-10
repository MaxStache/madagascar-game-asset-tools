from lib.writer import _write_u8, _write_u16
from rwConstants import RWSectionType
from lib.parser import Parser
from rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise
from dataclasses import dataclass, field
import io

from .STRING_0002 import RW_String
from .EXTENSION_0003 import RW_Extension


@dataclass
class RW_Texture_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    filterMode: int = 0  # u8
    addressModes: int = 0  # u8
    useMipLevels: bool = False  # u16

    @staticmethod
    def read(parser: Parser) -> "RW_Texture_Struct":
        texture_s = RW_Texture_Struct()
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

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_u8(buf, this.filterMode)
        _write_u8(buf, this.addressModes)
        _write_u16(buf, this.useMipLevels)

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

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_Texture":
        texture = RW_Texture()
        texture.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texture.header,
            RWSectionType.rwID_TEXTURE.value,
            "RW_Texture chunk type",
        )

        texture.struct = RW_Texture_Struct.read(parser)

        texture.diffuseTextureName = RW_String.read(parser)

        texture.alphaTextureName = RW_String.read(parser)

        texture.extension = RW_Extension.read(
            parser, parent_type=RWSectionType.rwID_TEXTURE.value
        )

        return texture

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)

        this.diffuseTextureName.write(buf, stamp)

        this.alphaTextureName.write(buf, stamp)

        this.extension.write(buf, stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_TEXTURE.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
