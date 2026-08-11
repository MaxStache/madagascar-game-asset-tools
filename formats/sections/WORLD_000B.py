import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import (
    RW_Section,
    RWHeader,
    Vector3,
    expect_chunk_type_or_raise,
)
from formats.lib.writer import write_u32
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

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_World_Struct":
        world_s = cls()
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
 
    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u32(buf, self.rootIsWorldSector)
        self.inverseOrigin.write(buf)

        if self._struct_size not in (0x30, 0x40):
            raise ValueError(
                f"Unexpected RW_WorldStruct payload size: {self._struct_size}. Could not determine to write a struct type A or B! For more information look into docs!"
            )

        if self._struct_size == 0x40:
            write_u32(buf, self.numTriangles)
            write_u32(buf, self.numVertices)
            write_u32(buf, self.numPlaneSectors)
            write_u32(buf, self.numAtomicSectors)
            write_u32(buf, self.colSectorSize)
            write_u32(buf, self.worldFlags.encode())
            self.boxMax.write(buf)
            self.boxMin.write(buf)
        elif self._struct_size == 0x30:
            self.boxMax.write(buf)
            write_u32(buf, self.numTriangles)
            write_u32(buf, self.numVertices)
            write_u32(buf, self.numPlaneSectors)
            write_u32(buf, self.numAtomicSectors)
            write_u32(buf, self.colSectorSize)
            write_u32(buf, self.worldFlags.encode())

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

    root_sector: RW_PlaneSector | RW_AtomicSector | None = field(default=None)

    extension: RW_Extension = field(default_factory=RW_Extension)

    @property
    def worldFlags(self) -> RpWorldFlags:
        """Exposed so children (sectors) can resolve worldFlags from their parent."""
        return self.struct.worldFlags

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_World":
        world = cls()
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

        world.struct.worldFlags.print()

        return world

    @override
    def write(self, f, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        self.struct.write(buf, stamp, parent=self)
        self.material_list.write(buf, stamp, parent=self)

        assert self.root_sector is not None, "Root sector is None. Cannot write RW_World without a root sector."
        self.root_sector.write(buf, stamp, parent=self)

        self.extension.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_WORLD.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    def collect_atomic_sectors(self) -> list[RW_AtomicSector]:
        if self.root_sector is None:
            return []

        sectors: list[RW_AtomicSector] = []
        if isinstance(self.root_sector, RW_AtomicSector):
            sectors.append(self.root_sector)
        else:
            sectors.extend(self.root_sector.collect_atomic_sectors())

        return sectors