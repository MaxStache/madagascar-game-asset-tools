import io
from dataclasses import dataclass, field

from ..lib.writer import _write_u32
from ..lib.parser import Parser
from ..rwConstants import RWSectionType
from ..rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from .GEOMETRY_000F import RW_Geometry

@dataclass
class RW_GeometryList_Struct(RW_Section):
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
class RW_GeometryList(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_GeometryList_Struct = field(default_factory=RW_GeometryList_Struct)

    geometries: list[RW_Geometry] = field(default_factory=list)  # RW_Geometry each

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

    header: RWHeader = field(default_factory=RWHeader)