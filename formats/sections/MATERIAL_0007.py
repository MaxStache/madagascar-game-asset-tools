import io
from dataclasses import dataclass, field
from typing import Optional

from lib.parser import Parser
from lib.writer import _write_u32, _write_f32
from rwConstants import RWSectionType
from rw_basics import RW_Section, RWColor32, RWHeader, expect_chunk_type_or_raise
from .TEXTURE_0006 import RW_Texture
from .EXTENSION_0003 import RW_Extension


@dataclass
class RW_Material_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    flags: int = 0
    color: RWColor32 = field(default_factory=RWColor32)
    unknown: int = 0x1C2DE734  # Probably also some flags
    isTextured: int = 0

    ambient: float = 0.0
    specular: float = 0.0
    diffuse: float = 0.0

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_Material_Struct":
        mat_s = RW_Material_Struct()
        mat_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            mat_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_Material_Struct chunk type",
        )

        mat_s.flags = parser.readUint32()
        mat_s.color = RWColor32.read(parser)
        mat_s.unknown = parser.readUint32()
        mat_s.isTextured = parser.readUint32()

        mat_s.ambient = parser.readFloat()
        mat_s.specular = parser.readFloat()
        mat_s.diffuse = parser.readFloat()

        return mat_s

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_u32(buf, this.flags)
        this.color.write(buf)
        _write_u32(buf, this.unknown)
        _write_u32(buf, this.isTextured)

        _write_f32(buf, this.ambient)
        _write_f32(buf, this.specular)
        _write_f32(buf, this.diffuse)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_Material(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_Material_Struct = field(default_factory=RW_Material_Struct)

    # if struct.isTextured
    texture: Optional[RW_Texture] = None
    # endifs

    extension: RW_Extension = field(default_factory=RW_Extension)

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_Material":
        mat = RW_Material()
        mat.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            mat.header,
            RWSectionType.rwID_MATERIAL.value,
            "RW_Material chunk type",
        )

        mat.struct = RW_Material_Struct.read(
            parser, parent_type=RWSectionType.rwID_MATERIAL.value
        )

        if mat.struct.isTextured:
            mat.texture = RW_Texture.read(parser)

        mat.extension = RW_Extension.read(parser, parent_type=RWSectionType.rwID_MATERIAL.value)

        return mat

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)

        if this.struct.isTextured and this.texture is not None:
            this.texture.write(buf, stamp)

        this.extension.write(buf, stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATERIAL.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())