"""
rwDFF.py — RenderWare Model (.DFF) Library
========================================================

Read, write, export, and import Renderware DFF files.

"""

import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union
from lib.parser import Parser
from rwConstants import RWSectionType, DEFAULT_VERSION_STAMP
from rw_basics import (
    RW_UV,
    RW_GeometryTriangle,
    RW_Matrix3x3,
    RWColor32,
    RWSphere,
    Vector3,
    RWHeader,
    expect_chunk_type_or_raise,
    library_id_unpack,
)
from sections import RW_Material

__version__ = "1.0.0"


@dataclass
class RW_MaterialList:
    header: RWHeader = field(default_factory=RWHeader)
    struct_header: RWHeader = field(default_factory=RWHeader)

    material_count: int = 0

    # A material index equals -1 if it ^++^+is a material.
    # If the material is an instance of a previously defined material,
    # the index equals the base materials one.
    #    ~ gtamods.com/wiki/Material_List_(RW_Section)
    materialIndices: list[int] = field(
        default_factory=list
    )  # uint32 each material_count

    materials: list[RW_Material] = field(
        default_factory=list
    )  # RW_Material each material_count

    @staticmethod
    def read(parser: Parser) -> "RW_MaterialList":
        matlist = RW_MaterialList()
        matlist.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            matlist.header,
            RWSectionType.rwID_MATLIST.value,
            "RW_MaterialList chunk type",
        )
        matlist.struct_header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            matlist.struct_header,
            RWSectionType.rwID_STRUCT.value,
            "RW_MaterialList struct chunk type",
        )

        matlist.material_count = parser.readUint32()

        matlist.materialIndices = []
        for _ in range(matlist.material_count):
            val = parser.readInt32()
            matlist.materialIndices.append(val)

        matlist.materials = []
        for _ in range(matlist.material_count):
            matlist.materials.append(RW_Material.read(parser))

        return matlist

    def write(this, f, stamp):
        buf = io.BytesIO()
        sbuf = io.BytesIO()

        # region struct data
        matcount = len(this.materials)

        _write_u32(sbuf, matcount)

        if len(this.materialIndices) != matcount:
            raise ValueError(
                f"Failed to write MATLIST! {matcount} materials but materialIndices has {len(this.materialIndices)} entries"
            )
        for idx in this.materialIndices:
            _write_s32(sbuf, idx)
        # endregion

        buf.write(sbuf.getvalue())

        for mat in this.materials:
            mat.write(buf, stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATLIST.value,
            size=len(buf.getvalue()) + RWHeader().binSize,
            library_id_stamp=stamp,
        )
        rw_struct_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(sbuf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(rw_struct_header.pack())
        f.write(buf.getvalue())


@dataclass
class RpAtomicFlags:
    # https://gtamods.com/wiki/Atomic_(RW_Section)
    collision_test: bool = (
        False  # 0x00000001 — Include this atomic in RenderWare's collision system.
    )
    render: bool = False  # 0x00000004 — Render this atomic when it is inside the camera's view frustum. Almost every visible model has this enabled.

    @staticmethod
    def decode(value: int) -> "RpAtomicFlags":
        f = RpAtomicFlags()

        f.collision_test = bool(value & 0x00000001)
        f.render = bool(value & 0x00000004)

        return f

    def encode(self) -> int:
        v = 0

        if self.collision_test:
            v |= 0x00000001
        if self.render:
            v |= 0x00000004

        return v

    def print(self):
        print("RpAtomicFlags:")
        print(f"  collision_test: {self.collision_test}")
        print(f"  render: {self.render}")


@dataclass
class RW_Atomic_Struct:
    header: RWHeader = field(default_factory=RWHeader)

    frame_index: int = 0  # u32
    geometry_index: int = 0  # u32
    flags: RpAtomicFlags = field(default_factory=RpAtomicFlags)
    unused: int = 0  # u32

    @staticmethod
    def read(parser: Parser) -> "RW_Atomic_Struct":
        atomic_s = RW_Atomic_Struct()
        atomic_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            atomic_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_Atomic_Struct chunk type",
        )

        atomic_s.frame_index = parser.readUint32()
        atomic_s.geometry_index = parser.readUint32()
        atomic_s.flags = RpAtomicFlags.decode(parser.readUint32())
        atomic_s.unused = parser.readUint32()

        return atomic_s

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_u32(buf, this.frame_index)  # frame_index
        _write_u32(buf, this.geometry_index)  # geometry_index
        _write_u32(buf, this.flags.encode())  # flags
        _write_u32(buf, this.unused)  # unused

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_Atomic:
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_Atomic_Struct = field(default_factory=RW_Atomic_Struct)

    ext_header: RWHeader = field(default_factory=RWHeader)
    extData: bytes = b""  # ext_header.payload_size

    @staticmethod
    def read(parser: Parser) -> "RW_Atomic":
        atomic = RW_Atomic()
        atomic.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            atomic.header,
            RWSectionType.rwID_ATOMIC.value,
            "RW_Atomic chunk type",
        )

        atomic.struct = RW_Atomic_Struct.read(parser)

        atomic.ext_header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            atomic.ext_header,
            RWSectionType.rwID_EXTENSION.value,
            "RW_Atomic extension chunk type",
        )
        atomic.extData = parser.readBytes(atomic.ext_header.size)

        return atomic

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)

        ext_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(this.extData),
            library_id_stamp=stamp,
        )
        buf.write(ext_header.pack())
        buf.write(this.extData)

        rw_header = RWHeader(
            type=RWSectionType.rwID_ATOMIC.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RpCameraProjectionMode:
    # https://gtamods.com/wiki/Camera_(RW_Section)
    perspective: bool = False  # 0x00000001 — Perspective projection
    parallel: bool = False  # 0x00000002 — Orthographic projection

    @staticmethod
    def decode(value: int) -> "RpAtomicFlags":
        f = RpAtomicFlags()

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
class RW_Camera_Struct:
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

    def write(this, f, stamp):
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
class RW_Camera:
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_Camera_Struct = field(default_factory=RW_Camera_Struct)

    ext_header: RWHeader = field(default_factory=RWHeader)
    extData: bytes = b""  # ext_header.payload_size

    @staticmethod
    def read(parser: Parser) -> "RW_Camera":
        cam = RW_Camera()
        cam.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            cam.header,
            RWSectionType.rwID_CAMERA.value,
            "RW_Camera chunk type",
        )

        cam.struct = RW_Camera_Struct.read(parser)

        cam.ext_header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            cam.ext_header,
            RWSectionType.rwID_EXTENSION.value,
            "RW_Camera extension chunk type",
        )
        cam.extData = parser.readBytes(cam.ext_header.size)

        return cam

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)

        ext_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(this.extData),
            library_id_stamp=stamp,
        )
        buf.write(ext_header.pack())
        buf.write(this.extData)

        rw_header = RWHeader(
            type=RWSectionType.rwID_CAMERA.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RpWorldFlags:
    triStrip: bool = False  # 0x00000001 — geometry uses triangle strips
    positions: bool = False  # 0x00000002 — has positions (should always be set)
    textured: bool = False  # 0x00000004 — has one set of texture coordinates
    preLit: bool = False  # 0x00000008 — has pre-lit vertex colors
    normals: bool = False  # 0x00000010 — has normals
    light: bool = False  # 0x00000020 — is lit
    modulateMaterialColor: bool = (
        False  # 0x00000040 — vertex colors modulate material color
    )
    textured2: bool = False  # 0x00000080 — has a second set of texture coordinates
    numTexCoordSets: int = (
        0  # bits 16–19 — number of UV sets (0 = auto-detect from other flags)
    )
    native: bool = False  # 0x01000000 — world is in native (platform-specific) format
    nativeInstance: bool = False  # 0x02000000 — world is a native instance
    sectorsOverlap: bool = False  # 0x40000000 — BSP sectors are allowed to overlap

    @staticmethod
    def decode(value: int) -> "RpWorldFlags":
        f = RpWorldFlags()
        f.triStrip = bool(value & 0x00000001)
        f.positions = bool(value & 0x00000002)
        f.textured = bool(value & 0x00000004)
        f.preLit = bool(value & 0x00000008)
        f.normals = bool(value & 0x00000010)
        f.light = bool(value & 0x00000020)
        f.modulateMaterialColor = bool(value & 0x00000040)
        f.textured2 = bool(value & 0x00000080)
        f.numTexCoordSets = (value >> 16) & 0xF
        f.native = bool(value & 0x01000000)
        f.nativeInstance = bool(value & 0x02000000)
        f.sectorsOverlap = bool(value & 0x40000000)
        return f

    def encode(self) -> int:
        v = 0
        if self.triStrip:
            v |= 0x00000001
        if self.positions:
            v |= 0x00000002
        if self.textured:
            v |= 0x00000004
        if self.preLit:
            v |= 0x00000008
        if self.normals:
            v |= 0x00000010
        if self.light:
            v |= 0x00000020
        if self.modulateMaterialColor:
            v |= 0x00000040
        if self.textured2:
            v |= 0x00000080
        v |= (self.numTexCoordSets & 0xF) << 16
        if self.native:
            v |= 0x01000000
        if self.nativeInstance:
            v |= 0x02000000
        if self.sectorsOverlap:
            v |= 0x40000000
        return v

    def print(self):
        print("RpWorldFlags:")
        print(f"  triStrip: {self.triStrip}")
        print(f"  positions: {self.positions}")
        print(f"  textured: {self.textured}")
        print(f"  preLit: {self.preLit}")
        print(f"  normals: {self.normals}")
        print(f"  light: {self.light}")
        print(f"  modulateMaterialColor: {self.modulateMaterialColor}")
        print(f"  textured2: {self.textured2}")
        print(f"  numTexCoordSets: {self.numTexCoordSets}")
        print(f"  native: {self.native}")
        print(f"  nativeInstance: {self.nativeInstance}")
        print(f"  sectorsOverlap: {self.sectorsOverlap}")


@dataclass
class RW_Clump_Struct:
    header: RWHeader = field(default_factory=RWHeader)

    numAtomics: int = 0  # u32
    numLights: int = 0  # u32 - only present after version 0x33000
    numCameras: int = 0  # u32 - only present after version 0x33000

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_u32(buf, this.numAtomics)
        _write_u32(buf, this.numLights)
        _write_u32(buf, this.numCameras)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_Clump:
    header: RWHeader = field(default_factory=RWHeader)

    struct: "RW_Clump_Struct" = field(default_factory=RW_Clump_Struct)

    atomics: list[RW_Atomic] = field(default_factory=list)

    camera_frame_indices: list[int] = field(default_factory=list)  # u32 each numCameras
    cameras: list[RW_Camera] = field(default_factory=list)

    ext_header: RWHeader = field(default_factory=RWHeader)
    extData: bytes = b""  # ext_header.payload_size

    def save(self, filepath: Union[str, Path]):
        buf = io.BytesIO()

        stamp = DEFAULT_VERSION_STAMP

        self.struct.write(buf, stamp)

        for atomic in self.atomic:
            atomic.write(buf, stamp)

        ext_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(self.extData),
            library_id_stamp=DEFAULT_VERSION_STAMP,
        )
        buf.write(ext_header.pack())
        buf.write(self.extData)

        rw_header = RWHeader(
            type=RWSectionType.rwID_WORLD.value,
            size=len(buf.getvalue()),
            library_id_stamp=DEFAULT_VERSION_STAMP,
        )
        with open(filepath, "wb") as f:
            f.write(rw_header.pack())
            f.write(buf.getvalue())


@dataclass
class RW_Frame:
    header: RWHeader = field(default_factory=RWHeader)

    rotation_matrix: RW_Matrix3x3 = field(default_factory=RW_Matrix3x3)
    position: Vector3 = field(default_factory=Vector3)
    parent_idx: int = -1  # i32
    matrix_flags: int = 0  # u32 - see https://gtamods.com/wiki/Talk:Frame_List_(RW_Section)#Flags_under_Frame_Data

    @staticmethod
    def read(parser: Parser) -> "RW_Frame":
        frame = RW_Frame()
        frame.rotation_matrix = RW_Matrix3x3.read(parser)
        frame.position = Vector3.read(parser)
        frame.parent_idx = parser.readInt32()
        frame.matrix_flags = parser.readUint32()

        return frame

    def write(this, f):
        this.rotation_matrix.write(f)
        this.position.write(f)
        _write_s32(f, this.parent_idx)
        _write_u32(f, this.matrix_flags)


@dataclass
class RW_FrameList_Struct:
    header: RWHeader = field(default_factory=RWHeader)

    frame_count: int = 0  # u32
    frames: list[RW_Frame] = field(default_factory=list)  # RW_Frame each

    @staticmethod
    def read(parser: Parser) -> "RW_FrameList_Struct":
        fl_struct = RW_FrameList_Struct()
        fl_struct.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            fl_struct.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_FrameList_Struct chunk type",
        )

        fl_struct.frame_count = parser.readUint32()
        fl_struct.frames = []
        for _ in range(fl_struct.frame_count):
            fl_struct.frames.append(RW_Frame.read(parser))

        return fl_struct

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_u32(buf, len(this.frames))  # frame_count
        for frame in this.frames:
            frame.write(buf)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_FrameList:
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_FrameList_Struct = field(default_factory=RW_FrameList_Struct)

    ext_header_list: list[RWHeader] = field(default_factory=list)
    extData_list: list[bytes] = field(default_factory=list)  # ext_header.payload_size

    @staticmethod
    def read(parser: Parser) -> "RW_FrameList":
        framelist = RW_FrameList()
        framelist.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            framelist.header,
            RWSectionType.rwID_FRAMELIST.value,
            "RW_FrameList chunk type",
        )

        section_end = parser.tell() + framelist.header.size

        framelist.struct = RW_FrameList_Struct.read(parser)

        while parser.tell() < section_end:
            ext_header = RWHeader.read(parser)
            expect_chunk_type_or_raise(
                ext_header,
                RWSectionType.rwID_EXTENSION.value,
                "RW_FrameList extension chunk type",
            )
            ext_data = parser.readBytes(ext_header.size)

            framelist.ext_header_list.append(ext_header)
            framelist.extData_list.append(ext_data)

        if parser.tell() != section_end:
            raise ValueError(
                f"RW_FrameList parsing ended at offset {parser.tell()}, expected {section_end}"
            )

        return framelist

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)

        ext_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(this.extData),
            library_id_stamp=stamp,
        )
        buf.write(ext_header.pack())
        buf.write(this.extData)

        rw_header = RWHeader(
            type=RWSectionType.rwID_FRAMELIST.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_GeometryList_Struct:
    header: RWHeader = field(default_factory=RWHeader)

    numGeometries: int = 0  # u32

    @staticmethod
    def read(parser: Parser) -> "RW_GeometryList_Struct":
        gl_struct = RW_GeometryList_Struct()
        gl_struct.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            gl_struct.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_GeometryList_Struct chunk type",
        )

        gl_struct.numGeometries = parser.readUint32()

        return gl_struct

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_u32(buf, this.numGeometries)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RpGeometryFlags:
    # https://gtamods.com/wiki/RpGeometry#Format
    triStrip: bool = False  # 0x00000001 — geometry uses triangle strips
    positions: bool = False  # 0x00000002 — has vertex positions
    textured: bool = False  # 0x00000004 — has texture coordinates
    preLit: bool = False  # 0x00000008 — has vertex colors
    normals: bool = False  # 0x00000010 — has normals
    light: bool = False  # 0x00000020 — geometry is lit
    modulateMaterialColor: bool = False  # 0x00000040
    textured2: bool = False  # 0x00000080 — has second UV set
    numTexCoordSets: int = 0  # bits 16-23
    native: bool = False  # 0x01000000 — native geometry

    @staticmethod
    def decode(value: int) -> "RpGeometryFlags":
        f = RpGeometryFlags()

        f.triStrip = bool(value & 0x00000001)
        f.positions = bool(value & 0x00000002)
        f.textured = bool(value & 0x00000004)
        f.preLit = bool(value & 0x00000008)
        f.normals = bool(value & 0x00000010)
        f.light = bool(value & 0x00000020)
        f.modulateMaterialColor = bool(value & 0x00000040)
        f.textured2 = bool(value & 0x00000080)

        # bits 16-23
        f.numTexCoordSets = (value >> 16) & 0xFF

        f.native = bool(value & 0x01000000)

        return f

    def encode(self) -> int:
        v = 0

        if self.triStrip:
            v |= 0x00000001
        if self.positions:
            v |= 0x00000002
        if self.textured:
            v |= 0x00000004
        if self.preLit:
            v |= 0x00000008
        if self.normals:
            v |= 0x00000010
        if self.light:
            v |= 0x00000020
        if self.modulateMaterialColor:
            v |= 0x00000040
        if self.textured2:
            v |= 0x00000080

        v |= (self.numTexCoordSets & 0xFF) << 16

        if self.native:
            v |= 0x01000000

        return v

    def print(self):
        print("RpGeometryFlags:")
        print(f"  triStrip: {self.triStrip}")
        print(f"  positions: {self.positions}")
        print(f"  textured: {self.textured}")
        print(f"  preLit: {self.preLit}")
        print(f"  normals: {self.normals}")
        print(f"  light: {self.light}")
        print(f"  modulateMaterialColor: {self.modulateMaterialColor}")
        print(f"  textured2: {self.textured2}")
        print(f"  numTexCoordSets: {self.numTexCoordSets}")
        print(f"  native: {self.native}")


@dataclass
class RW_Geometry_Struct_MorphTarget:
    """NOTE: This is not a RW section!!!"""

    boundingSphere: RWSphere = field(default_factory=RWSphere)
    hasVertices: bool = False  # u32
    hasNormals: bool = False  # u32

    # if hasVertices:
    vertices: list[Vector3] = field(default_factory=list)  # Vector3 each
    # endif

    # if hasNormals:
    normals: list[Vector3] = field(default_factory=list)  # Vector3 each
    # endif


@dataclass
class RW_Geometry_Struct:
    header: RWHeader = field(default_factory=RWHeader)

    format: RpGeometryFlags = field(default_factory=RpGeometryFlags)  # u32
    numTriangles: int = 0  # u32
    numVertices: int = 0  # u32
    numMorphTargets: int = 0  # u32

    # if version <= 0x34000
    ambient: float = 0.0  # f32
    specular: float = 0.0  # f32
    diffuse: float = 0.0  # f32
    # endif

    preLitColors: list[RWColor32] = field(
        default_factory=list
    )  # RWColor32 each numVertices
    texCordSets: list[list[RW_UV]] = field(
        default_factory=list
    )  # RW_UV each numVertices * numTexCoordSets

    triangles: list[RW_GeometryTriangle] = field(
        default_factory=list
    )  # RW_GeometryTriangle each numTriangles

    morphTargets: list[RW_Geometry_Struct_MorphTarget] = field(
        default_factory=list
    )  # RW_Geometry_Struct_MorphTarget each numMorphTargets

    @staticmethod
    def read(parser: Parser) -> "RW_Geometry_Struct":
        geo_s = RW_Geometry_Struct()
        geo_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            geo_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_Geometry_Struct chunk type",
        )

        geo_s.format = RpGeometryFlags.decode(parser.readUint32())
        geo_s.numTriangles = parser.readUint32()
        geo_s.numVertices = parser.readUint32()
        geo_s.numMorphTargets = parser.readUint32()

        if geo_s.header.version <= 0x34000:
            geo_s.ambient = parser.readFloat()
            geo_s.specular = parser.readFloat()
            geo_s.diffuse = parser.readFloat()

        if not geo_s.format.native:
            if geo_s.format.preLit:
                geo_s.preLitColors = []
                for _ in range(geo_s.numVertices):
                    geo_s.preLitColors.append(RWColor32.read(parser))

            # region UV sets
            uvSetCount = geo_s.format.numTexCoordSets
            if uvSetCount == 0:
                # auto-detect from other flags
                if geo_s.format.textured:
                    uvSetCount = 1
                if geo_s.format.textured2:
                    uvSetCount = 2

            for _ in range(uvSetCount):
                uv_set = []
                for _ in range(geo_s.numVertices):
                    uv_set.append(RW_UV(u=parser.readFloat(), v=parser.readFloat()))
                geo_s.texCordSets.append(uv_set)
            # endregion

            for _ in range(geo_s.numTriangles):
                v2 = parser.readInt16()
                v1 = parser.readInt16()
                mi = parser.readInt16()
                v3 = parser.readInt16()
                tri = RW_GeometryTriangle(v2, v1, mi, v3)
                geo_s.triangles.append(tri)

        for _ in range(geo_s.numMorphTargets):
            mt = RW_Geometry_Struct_MorphTarget()
            mt.boundingSphere = RWSphere.read(parser)
            mt.hasVertices = bool(parser.readInt32())
            mt.hasNormals = bool(parser.readInt32())

            if mt.hasVertices:
                mt.vertices = []
                for _ in range(geo_s.numVertices):
                    mt.vertices.append(Vector3.read(parser))

            if mt.hasNormals:
                mt.normals = []
                for _ in range(geo_s.numVertices):
                    mt.normals.append(Vector3.read(parser))

            geo_s.morphTargets.append(mt)

        return geo_s

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_u32(buf, this.format.encode())  # format
        _write_u32(buf, this.numTriangles)  # numTriangles
        _write_u32(buf, this.numVertices)  # numVertices
        _write_u32(buf, this.numMorphTargets)  # numMorphTargets

        if library_id_unpack(stamp) <= 0x34000:
            _write_f32(buf, this.ambient)
            _write_f32(buf, this.specular)
            _write_f32(buf, this.diffuse)

        if not this.format.native:
            if this.format.preLit:
                for color in this.preLitColors:
                    color.write(buf)

            # region UV sets
            for uv_set in this.texCordSets:
                for uv in uv_set:
                    _write_f32(buf, uv.u)
                    _write_f32(buf, uv.v)
            # endregion

            for tri in this.triangles:
                _write_u16(buf, tri.v2)
                _write_u16(buf, tri.v1)
                _write_u16(buf, tri.material_index)
                _write_u16(buf, tri.v3)

            for mt in this.morphTargets:
                mt.boundingSphere.write(buf)
                _write_u32(buf, int(mt.hasVertices))
                _write_u32(buf, int(mt.hasNormals))

                if mt.hasVertices:
                    for v in mt.vertices:
                        v.write(buf)

                if mt.hasNormals:
                    for n in mt.normals:
                        n.write(buf)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_Geometry:
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_Geometry_Struct = field(default_factory=RW_Geometry_Struct)

    material_list: RW_MaterialList = field(default_factory=RW_MaterialList)

    ext_header: RWHeader = field(default_factory=RWHeader)
    extData: bytes = b""  # ext_header.payload_size

    @staticmethod
    def read(parser: Parser) -> "RW_Geometry":
        geo = RW_Geometry()
        geo.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            geo.header,
            RWSectionType.rwID_GEOMETRY.value,
            "RW_Geometry chunk type",
        )

        geo.struct = RW_Geometry_Struct.read(parser)
        geo.material_list = RW_MaterialList.read(parser)

        geo.ext_header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            geo.ext_header,
            RWSectionType.rwID_EXTENSION.value,
            "RW_Geometry extension chunk type",
        )
        geo.extData = parser.readBytes(size=geo.ext_header.size)

        return geo

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)
        this.material_list.write(buf, stamp)

        ext_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(this.extData),
            library_id_stamp=stamp,
        )
        buf.write(ext_header.pack())
        buf.write(this.extData)

        rw_header = RWHeader(
            type=RWSectionType.rwID_GEOMETRY.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_GeometryList:
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_GeometryList_Struct = field(default_factory=RW_GeometryList_Struct)

    geometries: list[RW_Geometry] = field(default_factory=list)  # RW_Geometry each

    ext_header: RWHeader = field(default_factory=RWHeader)
    extData: bytes = b""  # ext_header.payload_size

    @staticmethod
    def read(parser: Parser) -> "RW_GeometryList":
        geolist = RW_GeometryList()
        geolist.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            geolist.header,
            RWSectionType.rwID_GEOMETRYLIST.value,
            "RW_GeometryList chunk type",
        )

        geolist.struct = RW_GeometryList_Struct.read(parser)

        geolist.geometries = []
        for _ in range(geolist.struct.numGeometries):
            geolist.geometries.append(RW_Geometry.read(parser))

        return geolist

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)

        for geo in this.geometries:
            geo.write(buf, stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_GEOMETRYLIST.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


# ═══════════════════════════════════════════════════════
#  helpers
# ═══════════════════════════════════════════════════════


def _write_u8(f, v):
    f.write(struct.pack("<B", v))


def _write_u16(f, v):
    f.write(struct.pack("<H", v))


def _write_u32(f, v):
    f.write(struct.pack("<I", v))


def _write_s32(f, v):
    f.write(struct.pack("<i", v))


def _write_f32(f, v):
    f.write(struct.pack("<f", v))


def load_dff(filepath: Union[str, Path]) -> RW_Clump:
    """Load a DFF file from disk

    Args:
        filepath: Path to the .dff file.

    Returns:
        Parsed DFF.
    """
    dff = RW_Clump()

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

        dff.header = RWHeader.read(parser)

        expect_chunk_type_or_raise(
            dff.header,
            RWSectionType.rwID_CLUMP.value,
            "Not a RW DFF (TOP)",
        )

        # Clump Struct
        # ===================
        dff.struct = RW_Clump_Struct()
        dff.struct.header = RWHeader.read(parser)

        expect_chunk_type_or_raise(
            dff.struct.header,
            RWSectionType.rwID_STRUCT.value,
            "Not a RW DFF (TOP_STRUCT)",
        )

        dff.struct.numAtomics = parser.readUint32()
        dff.struct.numLights = parser.readUint32()
        dff.struct.numCameras = parser.readUint32()

        # Frame List
        # ===================
        dff.frame_list = RW_FrameList.read(parser)

        # Geometry List
        # ===================
        dff.geometry_list = RW_GeometryList.read(parser)

        # Atomics follow the geometry list in DFF clumps, but some files do not
        # actually contain the advertised number of atomic chunks.
        dff.atomics = []
        for _ in range(dff.struct.numAtomics):
            dff.atomics.append(RW_Atomic.read(parser))

        
        if dff.struct.numLights > 0:
            raise NotImplementedError(
                f"RW_Clump has {dff.struct.numLights} lights, but light parsing is not implemented"
            )
        
        for _ in range(dff.struct.numCameras):
            parser.readRWChunkHeader()  # skip
            dff.camera_frame_indices.append(parser.readUint32())
            dff.cameras.append(RW_Camera.read(parser))


        dff.ext_header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            dff.ext_header,
            RWSectionType.rwID_EXTENSION.value,
            "Not a RW DFF (TOP_EXTENSION)",
        )
        if parser.getRemainingBytes() < dff.ext_header.size:
            raise ValueError(
                f"Declared extension data size {dff} exceeds remaining file size {parser.getRemainingBytes()}"
            )
        dff.extData = parser.readBytes(dff.ext_header.size)

    return dff
