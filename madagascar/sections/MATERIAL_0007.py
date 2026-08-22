import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from madagascar.lib.parser import Parser
from madagascar.lib.writer import write_u32, write_f32
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWColor32, RWHeader, expect_chunk_type_or_raise
from madagascar.sections.TEXTURE_0006 import RW_Texture
from madagascar.sections.EXTENSION_0003 import RW_Extension


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

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Material_Struct":
        mat_s = cls()
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

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u32(buf, self.flags)
        self.color.write(buf)
        write_u32(buf, self.unknown)
        write_u32(buf, self.isTextured)

        write_f32(buf, self.ambient)
        write_f32(buf, self.specular)
        write_f32(buf, self.diffuse)

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
    texture: RW_Texture | None = None
    # endifs

    extension: RW_Extension = field(default_factory=RW_Extension)

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Material":
        mat = RW_Material()
        mat.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            mat.header,
            RWSectionType.rwID_MATERIAL.value,
            "RW_Material chunk type",
        )

        mat.struct = RW_Material_Struct.read(
            parser, parent=mat
        )

        if mat.struct.isTextured:
            mat.texture = RW_Texture.read(parser)

        mat.extension = RW_Extension.read(parser, parent=mat)

        return mat

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        self.struct.write(buf, stamp)

        if self.struct.isTextured and self.texture is not None:
            self.texture.write(buf, stamp, parent=self)

        self.extension.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATERIAL.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())