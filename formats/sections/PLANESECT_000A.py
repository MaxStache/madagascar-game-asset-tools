import io
from dataclasses import dataclass, field
from typing import BinaryIO, Union, override

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise, RW_Axis_Type
from formats.lib.writer import write_f32, write_u32
from formats.sections.ATOMICSECT_0009 import RW_AtomicSector
from formats.sections.shared.worldflags import RpWorldFlags



@dataclass
class RW_PlaneSector_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    type: RW_Axis_Type = RW_Axis_Type.rwPLANE_X  # uint32 (axis)
    value: float = 0.0  # float32
    """
    value - the position of that plane along the chosen axis,
    i.e. the axis offset of the dividing plane.
    If type == 4 (Y) and value == 100.0,
    the plane is y = 100. To decide which side a point falls on,
    you read the point's coordinate at the axis given by type and compare
    it against value: less goes to the negative/left subtree, greater-or-equal goes
    to the positive/right subtree. For an axis-aligned plane self comparison is the
    dot-product test the overview section describes
    it collapses to picking one coordinate.
    
    REFRENCE TO: RenderWare Whitepapers - worlds.pdf
    WRITTEN BY: Claude Opus 4.8 Extra
    """

    left_is_atomic: int = 0  # uint32
    right_is_atomic: int = 0  # uint32

    left_value: float = 0.0  # float32
    right_value: float = 0.0  # float32

    """
    left_value and right_value:
    those exist because RenderWare allows sectors to overlap (page 10).
    value is the nominal split position, while left_value and right_value are 
    the actual extents of the negative and positive sub-boxes, which may overlap rather 
    than meeting exactly at value. That's the mechanism that lets the builder avoid cutting 
    geometry at the plane.
    
    REFRENCE TO: RenderWare Whitepapers - worlds.pdf
    WRITTEN BY: Claude Opus 4.8 Extra
    """

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_PlaneSector_Struct":
        ps_s = cls()
        ps_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            ps_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_PlaneSector_Struct chunk type",
        )

        ps_s.type = RW_Axis_Type(parser.readUint32())

        ps_s.value = parser.readFloat()

        ps_s.left_is_atomic = parser.readUint32()
        ps_s.right_is_atomic = parser.readUint32()

        ps_s.left_value = parser.readFloat()
        ps_s.right_value = parser.readFloat()

        return ps_s

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u32(buf, self.type.value)
        write_f32(buf, self.value)
        write_u32(buf, self.left_is_atomic)
        write_u32(buf, self.right_is_atomic)
        write_f32(buf, self.left_value)
        write_f32(buf, self.right_value)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_PlaneSector(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_PlaneSector_Struct = field(default_factory=RW_PlaneSector_Struct)

    left_child: Union["RW_PlaneSector", RW_AtomicSector, None] = field(default=None)
    right_child: Union["RW_PlaneSector", RW_AtomicSector, None] = field(default=None)

    # kept so children can resolve worldFlags from their parent; hidden from
    # repr to avoid repeating the flags at every tree node
    worldFlags: RpWorldFlags = field(default_factory=RpWorldFlags, repr=False)

    @classmethod
    @override
    def read(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, parser: Parser, parent: RW_Section | None = None, worldFlags: RpWorldFlags | None = None
    ) -> "RW_PlaneSector":
        assert worldFlags is not None, "worldFlags must be provided when reading RW_PlaneSector"
        ps = cls()
        ps.worldFlags = worldFlags
        ps.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            ps.header,
            RWSectionType.rwID_PLANESECT.value,
            "RW_PlaneSector chunk type",
        )

        ps.struct = RW_PlaneSector_Struct.read(parser, parent=ps)

        if ps.struct.left_is_atomic:
            expect_chunk_type_or_raise(
                RWHeader.peek(parser),
                RWSectionType.rwID_ATOMICSECT.value,
                "RW_PlaneSector left child chunk type",
            )
            ps.left_child = RW_AtomicSector.read(parser, parent=ps, worldFlags=worldFlags)
        else:
            expect_chunk_type_or_raise(
                RWHeader.peek(parser),
                RWSectionType.rwID_PLANESECT.value,
                "RW_PlaneSector left child chunk type",
            )
            ps.left_child = RW_PlaneSector.read(parser, parent=ps, worldFlags=worldFlags)
        
        if ps.struct.right_is_atomic:
            expect_chunk_type_or_raise(
                RWHeader.peek(parser),
                RWSectionType.rwID_ATOMICSECT.value,
                "RW_PlaneSector right child chunk type",
            )
            ps.right_child = RW_AtomicSector.read(parser, parent=ps, worldFlags=worldFlags)
        else:
            expect_chunk_type_or_raise(
                RWHeader.peek(parser),
                RWSectionType.rwID_PLANESECT.value,
                "RW_PlaneSector right child chunk type",
            )
            ps.right_child = RW_PlaneSector.read(parser, parent=ps, worldFlags=worldFlags)

        return ps

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        assert self.left_child is not None
        assert self.right_child is not None

        buf = io.BytesIO()

        self.struct.write(buf, stamp, parent=self)

        self.left_child.write(buf, stamp, parent=self)
        self.right_child.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_PLANESECT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    def collect_atomic_sectors(
        self,
    ) -> list[RW_AtomicSector]:
        assert self.left_child is not None
        assert self.right_child is not None

        sectors: list[RW_AtomicSector] = []

        if isinstance(self.left_child, RW_AtomicSector):
            sectors.append(self.left_child)
        else:
            sectors.extend(self.left_child.collect_atomic_sectors())

            
        if isinstance(self.right_child, RW_AtomicSector):
            sectors.append(self.right_child)
        else:
            sectors.extend(self.right_child.collect_atomic_sectors())

        return sectors
