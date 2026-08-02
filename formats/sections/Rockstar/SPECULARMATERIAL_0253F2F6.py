import io
from dataclasses import dataclass, field
from typing import override

from formats.lib.writer import write_f32
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_Rockstar_SpecularMaterial(RW_Section):
    """https://gtamods.com/wiki/Specular_Material_(RW_Section)"""
    header: RWHeader = field(default_factory=RWHeader)
    
    specular_level: float = field(default=0.0) # Specular Level (0.0-1.0)
    specular_texture_name: str = field(default="") # Specular Texture Name

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Rockstar_SpecularMaterial":
        specmat = cls()
        specmat.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            specmat.header,
            RWSectionType.rwID_rockstar_SpecularMaterial.value,
            "RW_Rockstar_SpecularMaterial chunk type",
        )

        specmat.specular_level = parser.readFloat()  # specular level

        specmat.specular_texture_name = parser.readBytes(24).decode("latin-1")  # specular texture name

        return specmat

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_f32(buf, self.specular_level)  # specular level

        encoded_texture_name = self.specular_texture_name.encode("latin-1")
        buf.write(encoded_texture_name.ljust(24, b"\x00"))

        rw_header = RWHeader(
            type=RWSectionType.rwID_rockstar_SpecularMaterial.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())