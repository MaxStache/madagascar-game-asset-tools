import io
from dataclasses import dataclass, field

from formats.lib.writer import _write_u32, _write_f32
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from formats.sections.EXTENSION_0003 import RW_Extension

@dataclass
class RpCameraProjectionMode:
    # https://gtamods.com/wiki/Camera_(RW_Section)
    perspective: bool = False  # 0x00000001 — Perspective projection
    parallel: bool = False  # 0x00000002 — Orthographic projection

    @staticmethod
    def decode(value: int) -> "RpCameraProjectionMode":
        f = RpCameraProjectionMode()

        f.perspective = bool(value & 0x00000001)
        f.parallel = bool(value & 0x00000002)

        return f

    def encode(self) -> int:
        v = 0

        if self.perspective:
            v |= 0x00000001
        if self.parallel:
            v |= 0x00000002

        return v

    def print(self):
        print("RpCameraProjectionMode:")
        print(f"  perspective: {self.perspective}")
        print(f"  parallel: {self.parallel}")

@dataclass
class RW_Camera_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    horizontalFOVTangent: float = 0  # f32
    verticalFOVTangent: float = 0  # f32
    viewportWidth: float = 0  # f32
    viewportHeight: float = 0  # f32
    nearPlane: float = 0  # f32
    farPlane: float = 0  # f32
    fogDistance: float = 0  # f32
    projectionMode: RpCameraProjectionMode = field(
        default_factory=RpCameraProjectionMode
    )

    @staticmethod
    def read(parser: Parser) -> "RW_Camera_Struct":
        cam_s = RW_Camera_Struct()
        cam_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            cam_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_Camera_Struct chunk type",
        )

        cam_s.horizontalFOVTangent = parser.readFloat()
        cam_s.verticalFOVTangent = parser.readFloat()
        cam_s.viewportWidth = parser.readFloat()
        cam_s.viewportHeight = parser.readFloat()
        cam_s.nearPlane = parser.readFloat()
        cam_s.farPlane = parser.readFloat()
        cam_s.fogDistance = parser.readFloat()
        cam_s.projectionMode = RpCameraProjectionMode.decode(parser.readUint32())

        return cam_s

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        _write_f32(buf, this.horizontalFOVTangent)
        _write_f32(buf, this.verticalFOVTangent)
        _write_f32(buf, this.viewportWidth)
        _write_f32(buf, this.viewportHeight)
        _write_f32(buf, this.nearPlane)
        _write_f32(buf, this.farPlane)
        _write_f32(buf, this.fogDistance)
        _write_u32(buf, this.projectionMode.encode())  # flags

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

@dataclass
class RW_Camera(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_Camera_Struct = field(default_factory=RW_Camera_Struct)

    extension: RW_Extension = field(default_factory=RW_Extension)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_Camera":
        cam = RW_Camera()
        cam.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            cam.header,
            RWSectionType.rwID_CAMERA.value,
            "RW_Camera chunk type",
        )

        cam.struct = RW_Camera_Struct.read(parser)

        cam.extension = RW_Extension.read(parser, parent=cam)

        return cam

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        this.struct.write(buf, stamp, parent=this)

        this.extension.write(buf, stamp, parent=this)

        rw_header = RWHeader(
            type=RWSectionType.rwID_CAMERA.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    header: RWHeader = field(default_factory=RWHeader)