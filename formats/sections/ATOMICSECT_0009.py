import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_UV, RW_Section, RW_Triangle, RWColor32, RWHeader, Vector3, expect_chunk_type_or_raise
from formats.lib.writer import write_f32, write_u16, write_u32
from formats.sections.shared.worldflags import RpWorldFlags
from formats.sections.EXTENSION_0003 import RW_Extension

@dataclass
class RW_AtomicSector_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    
    matListWindowBase: int = 0  # u32
    numTriangles: int = 0  # u32
    numVertices: int = 0  # u32

    boxMax: Vector3 = field(default_factory=Vector3)
    boxMin: Vector3 = field(default_factory=Vector3)

    collSectorPresent: int = 0  # u32
    unused: int = 0  # u32 always 0 in tested files

    vertices: list[Vector3] = field(default_factory=list, init=False)  # num_vertices

    # if not handled as collision bsp in TFB games
    colors: list[RWColor32] | None = field(
        default_factory=list, init=False
    )  # num_vertices
    uvs: list[RW_UV] | None = field(default_factory=list, init=False)  # num_vertices
    # endif

    triangles: list[RW_Triangle] = field(
        default_factory=list, init=False
    )  # num_triangles

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None, worldFlags: RpWorldFlags | None =None) -> "RW_AtomicSector_Struct":
        assert worldFlags is not None, "worldFlags must be provided to read RW_AtomicSector_Struct"
        atsec_s = RW_AtomicSector_Struct()
        atsec_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            atsec_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_AtomicSector_Struct chunk type",
        )
        payload_start = parser.tell()

        atsec_s.matListWindowBase = parser.readUint32()
        atsec_s.numTriangles = parser.readUint32()
        atsec_s.numVertices = parser.readUint32()

        atsec_s.boxMax = Vector3.read(parser)
        atsec_s.boxMin = Vector3.read(parser)

        atsec_s.collSectorPresent = parser.readUint32()
        atsec_s.unused = parser.readUint32()
        
        atsec_s.vertices = []
        for _ in range(atsec_s.numVertices):
            atsec_s.vertices.append(Vector3.read(parser))

        atsec_s.colors = []
        atsec_s.uvs = []

        if worldFlags.preLit:
            for _ in range(atsec_s.numVertices):
                atsec_s.colors.append(RWColor32.read(parser))

        # UV set count: explicit numTexCoordSets wins; otherwise derived
        # from the textured/textured2 flags.
        numUVSets = worldFlags.numTexCoordSets or (
            2 if worldFlags.textured2 else (1 if worldFlags.textured else 0)
        )
        if numUVSets > 1:
            raise NotImplementedError(
                f"Atomic sector has {numUVSets} UV sets; only 1 is supported."
            )
        if numUVSets:
            for _ in range(atsec_s.numVertices):
                atsec_s.uvs.append(RW_UV(u=parser.readFloat(), v=parser.readFloat()))

        atsec_s.triangles = []
        for _ in range(atsec_s.numTriangles):
            triangle = RW_Triangle()
            triangle.vertex1 = parser.readUint16()
            triangle.vertex2 = parser.readUint16()
            triangle.vertex3 = parser.readUint16()
            triangle.materialIndex = parser.readUint16()
            atsec_s.triangles.append(triangle)

        consumed = parser.tell() - payload_start
        if consumed != atsec_s.header.size:
            raise ValueError(
                f"RW_AtomicSector_Struct consumed {consumed} bytes but header "
                + f"declares {atsec_s.header.size} (numVertices={atsec_s.numVertices}, "
                + f"numTriangles={atsec_s.numTriangles}, worldFlags=0x{worldFlags.encode():08X})"
            )

        return atsec_s

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        worldFlags = getattr(parent, "worldFlags", None)
        if worldFlags is None:
            raise ValueError(
                "RW_AtomicSector_Struct.write needs the owning RW_AtomicSector as "
                + "`parent` to resolve worldFlags"
            )

        # The counts are what the reader trusts; keep them in sync with the
        # actual arrays so appending/rebuilding geometry can't desync them.
        self.numVertices = len(self.vertices)
        self.numTriangles = len(self.triangles)

        buf = io.BytesIO()

        write_u32(buf, self.matListWindowBase)
        write_u32(buf, self.numTriangles)
        write_u32(buf, self.numVertices)

        self.boxMax.write(buf)
        self.boxMin.write(buf)

        write_u32(buf, self.collSectorPresent)
        write_u32(buf, self.unused)

        for vertex in self.vertices:
            vertex.write(buf)

        if worldFlags.preLit:
            colors = self.colors or []
            if len(colors) != self.numVertices:
                raise ValueError(
                    f"rpWORLDPRELIT set but sector has {len(colors)} colors for "
                    + f"{self.numVertices} vertices"
                )
            for color in colors:
                color.write(buf)

        numUVSets = worldFlags.numTexCoordSets or (
            2 if worldFlags.textured2 else (1 if worldFlags.textured else 0)
        )
        if numUVSets > 1:
            raise NotImplementedError(
                f"Atomic sector has {numUVSets} UV sets; only 1 is supported."
            )
        if numUVSets:
            uvs = self.uvs or []
            if len(uvs) != self.numVertices:
                raise ValueError(
                    f"{numUVSets} UV set(s) declared but sector has {len(uvs)} UVs "
                    + f"for {self.numVertices} vertices"
                )
            for uv in uvs:
                write_f32(buf, uv.u)
                write_f32(buf, uv.v)

        for triangle in self.triangles:
            write_u16(buf, triangle.vertex1)
            write_u16(buf, triangle.vertex2)
            write_u16(buf, triangle.vertex3)
            write_u16(buf, triangle.materialIndex)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

@dataclass
class RW_AtomicSector(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    
    struct: RW_AtomicSector_Struct = field(default_factory=RW_AtomicSector_Struct)

    extension: RW_Extension = field(default_factory=RW_Extension)

    # kept so children can resolve worldFlags from their parent; hidden from
    # repr to avoid repeating the flags at every tree node
    worldFlags: RpWorldFlags = field(default_factory=RpWorldFlags, repr=False)

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None, worldFlags: RpWorldFlags) -> "RW_AtomicSector": # pyright: ignore[reportIncompatibleMethodOverride]
        atsec = cls()
        atsec.worldFlags = worldFlags
        atsec.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            atsec.header,
            RWSectionType.rwID_ATOMICSECT.value,
            "RW_AtomicSector chunk type",
        )

        atsec.struct = RW_AtomicSector_Struct.read(parser, parent=atsec, worldFlags=worldFlags)
        atsec.extension = RW_Extension.read(parser, parent=atsec)

        return atsec

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        self.struct.write(buf, stamp, parent=self)
        self.extension.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_ATOMICSECT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())