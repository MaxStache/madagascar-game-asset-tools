# noqa: N999
import io
from dataclasses import dataclass, field
from typing import override

from madagascar.lib.parser import Parser
from madagascar.lib.writer import write_u32, write_f32, write_u16
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise, RWSphere, RW_UV, RWColor32, RW_GeometryTriangle, Vector3, library_id_unpack

from madagascar.sections.MATLIST_0008 import RW_MaterialList

from madagascar.sections.EXTENSION_0003 import RW_Extension

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
class RW_Geometry_Struct(RW_Section):
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

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Geometry_Struct":
        geo_s = cls()
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
                uv_set: list[RW_UV] = []
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

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u32(buf, self.format.encode())  # format
        write_u32(buf, self.numTriangles)  # numTriangles
        write_u32(buf, self.numVertices)  # numVertices
        write_u32(buf, self.numMorphTargets)  # numMorphTargets

        if library_id_unpack(stamp)[0] <= 0x34000:
            write_f32(buf, self.ambient)
            write_f32(buf, self.specular)
            write_f32(buf, self.diffuse)

        if not self.format.native:
            if self.format.preLit:
                for color in self.preLitColors:
                    color.write(buf)

            # region UV sets
            for uv_set in self.texCordSets:
                for uv in uv_set:
                    write_f32(buf, uv.u)
                    write_f32(buf, uv.v)
            # endregion

            for tri in self.triangles:
                write_u16(buf, tri.vertex2)
                write_u16(buf, tri.vertex1)
                write_u16(buf, tri.materialIndex)
                write_u16(buf, tri.vertex3)

            for mt in self.morphTargets:
                mt.boundingSphere.write(buf)
                write_u32(buf, int(mt.hasVertices))
                write_u32(buf, int(mt.hasNormals))

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
class RW_Geometry(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_Geometry_Struct = field(default_factory=RW_Geometry_Struct)

    material_list: RW_MaterialList = field(default_factory=RW_MaterialList)

    extension: RW_Extension = field(default_factory=RW_Extension)

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Geometry":
        geo = cls()
        geo.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            geo.header,
            RWSectionType.rwID_GEOMETRY.value,
            "RW_Geometry chunk type",
        )

        geo.struct = RW_Geometry_Struct.read(parser)
        geo.material_list = RW_MaterialList.read(parser)

        geo.extension = RW_Extension.read(parser, parent=geo)

        return geo

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        self.struct.write(buf, stamp)
        self.material_list.write(buf, stamp, parent=self)

        self.extension.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_GEOMETRY.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
