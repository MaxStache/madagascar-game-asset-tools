import io
from dataclasses import dataclass, field

from formats.lib.writer import _write_f32
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise


@dataclass
class RW_Rockstar_ReflectionMaterial(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    environment_map_scale_x: float = field(default=0.0)  # f32 - Environment Map Scale X
    environment_map_scale_y: float = field(default=0.0)  # f32 - Environment Map Scale Y

    environment_map_offset_x: float = field(
        default=0.0
    )  # f32 - Environment Map Offset X
    environment_map_offset_y: float = field(
        default=0.0
    )  # f32 - Environment Map Offset Y

    reflection_intensity: float = field(
        default=0.0
    )  # f32 - Reflection Intensity (Shininess, 0.0-1.0)

    environment_texture_ptr: bytes = field(
        default=b""
    )  # 4b - Environment Texture Ptr, always 0 (zero)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_Rockstar_ReflectionMaterial":
        refmat = RW_Rockstar_ReflectionMaterial()
        refmat.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            refmat.header,
            RWSectionType.rwID_rockstar_ReflectionMaterial.value,
            "RW_Rockstar_ReflectionMaterial chunk type",
        )

        refmat.environment_map_scale_x = parser.readFloat()
        refmat.environment_map_scale_y = parser.readFloat()

        refmat.environment_map_offset_x = parser.readFloat()
        refmat.environment_map_offset_y = parser.readFloat()

        refmat.reflection_intensity = parser.readFloat()

        refmat.environment_texture_ptr = parser.readBytes(4)

        return refmat

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        _write_f32(buf, this.environment_map_scale_x)
        _write_f32(buf, this.environment_map_scale_y)

        _write_f32(buf, this.environment_map_offset_x)
        _write_f32(buf, this.environment_map_offset_y)

        _write_f32(buf, this.reflection_intensity)

        buf.write(this.environment_texture_ptr.pad(4, b"\x00"))

        rw_header = RWHeader(
            type=RWSectionType.rwID_rockstar_ReflectionMaterial.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
