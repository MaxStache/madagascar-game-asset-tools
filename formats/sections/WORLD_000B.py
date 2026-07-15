import io
from dataclasses import dataclass, field
from typing import Union

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import (
    RW_Section,
    RWHeader,
    Vector3,
    expect_chunk_type_or_raise,
)
from formats.lib.writer import _write_u32
from formats.sections.ATOMICSECT_0009 import RW_AtomicSector
from formats.sections.EXTENSION_0003 import RW_Extension
from formats.sections.MATLIST_0008 import RW_MaterialList
from formats.sections.PLANESECT_000A import RW_PlaneSector

from formats.sections.shared.worldflags import RpWorldFlags


@dataclass
class RW_World_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    _struct_size: int = 0  # size of the struct in bytes (not including header)

    rootIsWorldSector: int = 0  # often 0, "is root sector atomic?"
    inverseOrigin: Vector3 = field(default_factory=Vector3)  # often -0 -0 -0

    numTriangles: int = 0  # uint32
    numVertices: int = 0  # uint32
    numPlaneSectors: int = 0  # uint32
    numAtomicSectors: int = 0  # uint32
    colSectorSize: int = 0  # uint32
    worldFlags: RpWorldFlags = field(default_factory=RpWorldFlags)

    boxMax: Vector3 = field(default_factory=Vector3)
    boxMin: Vector3 = field(default_factory=Vector3)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_World_Struct":
        world_s = RW_World_Struct()
        world_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            world_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_World_Struct chunk type",
        )

        world_s.rootIsWorldSector = parser.readUint32()
        world_s.inverseOrigin = Vector3.read(parser)

        if world_s.header.size == 0x40:
            world_s.numTriangles = parser.readUint32()
            world_s.numVertices = parser.readUint32()
            world_s.numPlaneSectors = parser.readUint32()
            world_s.numAtomicSectors = parser.readUint32()
            world_s.colSectorSize = parser.readUint32()
            world_s.worldFlags = RpWorldFlags.decode(parser.readUint32())
            world_s.boxMax = Vector3.read(parser)
            world_s.boxMin = Vector3.read(parser)
            world_s._struct_size = 0x40
        elif world_s.header.size == 0x30:
            world_s.boxMax = Vector3.read(parser)
            world_s.numTriangles = parser.readUint32()
            world_s.numVertices = parser.readUint32()
            world_s.numPlaneSectors = parser.readUint32()
            world_s.numAtomicSectors = parser.readUint32()
            world_s.colSectorSize = parser.readUint32()
            world_s.worldFlags = RpWorldFlags.decode(parser.readUint32())
            world_s._struct_size = 0x30
        else:
            raise ValueError(
                f"Unexpected RW_WorldStruct payload size: {world_s.header.size}"
            )

        return world_s

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        _write_u32(buf, this.rootIsWorldSector)
        this.inverseOrigin.write(buf)

        if this._struct_size not in (0x30, 0x40):
            raise ValueError(
                f"Unexpected RW_WorldStruct payload size: {this._struct_size}. Could not determine to write a struct type A or B! For more information look into docs!"
            )

        if this._struct_size == 0x40:
            _write_u32(buf, this.numTriangles)
            _write_u32(buf, this.numVertices)
            _write_u32(buf, this.numPlaneSectors)
            _write_u32(buf, this.numAtomicSectors)
            _write_u32(buf, this.colSectorSize)
            _write_u32(buf, this.worldFlags.encode())
            this.boxMax.write(buf)
            this.boxMin.write(buf)
        elif this._struct_size == 0x30:
            this.boxMax.write(buf)
            _write_u32(buf, this.numTriangles)
            _write_u32(buf, this.numVertices)
            _write_u32(buf, this.numPlaneSectors)
            _write_u32(buf, this.numAtomicSectors)
            _write_u32(buf, this.colSectorSize)
            _write_u32(buf, this.worldFlags.encode())

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_World(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_World_Struct = field(default_factory=RW_World_Struct)

    material_list: RW_MaterialList = field(default_factory=RW_MaterialList)

    root_sector: Union[RW_PlaneSector, RW_AtomicSector] = (
        None  # can be either a plane sector or an atomic sector
    )

    extension: RW_Extension = field(default_factory=RW_Extension)

    @property
    def worldFlags(self) -> RpWorldFlags:
        """Exposed so children (sectors) can resolve worldFlags from their parent."""
        return self.struct.worldFlags

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_World":
        world = RW_World()
        world.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            world.header,
            RWSectionType.rwID_WORLD.value,
            "RW_World chunk type",
        )

        world.struct = RW_World_Struct.read(parser, parent=world)
        world.material_list = RW_MaterialList.read(parser, parent=world)

        peeked_root_sect_type = parser.peekUint32()
        if peeked_root_sect_type == RWSectionType.rwID_PLANESECT.value:
            world.root_sector = RW_PlaneSector.read(
                parser, parent=world, worldFlags=world.struct.worldFlags
            )
        elif peeked_root_sect_type == RWSectionType.rwID_ATOMICSECT.value:
            world.root_sector = RW_AtomicSector.read(
                parser, parent=world, worldFlags=world.struct.worldFlags
            )
        else:
            raise ValueError(
                f"Unexpected root sector type: {peeked_root_sect_type}. Expected either rwID_PLANESECT or rwID_ATOMICSECT."
            )

        world.extension = RW_Extension.read(parser, parent=world)

        return world

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        this.struct.write(buf, stamp, parent=this)
        this.material_list.write(buf, stamp, parent=this)

        this.root_sector.write(buf, stamp, parent=this)

        this.extension.write(buf, stamp, parent=this)

        rw_header = RWHeader(
            type=RWSectionType.rwID_WORLD.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    def collect_atomic_sectors(
        this,
    ) -> list[RW_AtomicSector]:
        if this.root_sector is None:
            return []

        sectors = []
        if isinstance(this.root_sector, RW_AtomicSector):
            sectors.append(this.root_sector)
        elif isinstance(this.root_sector, RW_PlaneSector):
            sectors.extend(this.root_sector.collect_atomic_sectors())
        else:
            raise ValueError(
                f"Unexpected root sector type: {type(this.root_sector)}. Expected either RW_PlaneSector or RW_AtomicSector."
            )

        return sectors
