from enum import IntEnum
import io
from dataclasses import dataclass, field
from typing import Union

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise
from formats.lib.writer import _write_f32, _write_u32
from formats.sections.ATOMICSECT_0009 import RW_AtomicSector
from formats.sections.shared.worldflags import RpWorldFlags


class RW_PlaneSector_Type(IntEnum):
    """
    These specific numbers aren't arbitrary,
    they're byte offsets into an RwV3d struct,
    which is just three consecutive floats {x, y, z} at offsets 0, 4, and 8.
    So the engine can use type directly to index the relevant coordinate of a point
    (that's what the GETCOORD macro in the headers does).
    You can see this in the whitepaper's iterator example: partition->type = 4;
    /* the y-axis */.

    REFRENCE TO: RenderWare Whitepapers - worlds.pdf
    WRITTEN BY: Claude Opus 4.8 Extra
    """

    rwPLANE_X = 0
    rwPLANE_Y = 4
    rwPLANE_Z = 8


@dataclass
class RW_PlaneSector_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    type: RW_PlaneSector_Type = RW_PlaneSector_Type.rwPLANE_X  # uint32 (axis)
    value: float = 0.0  # float32
    """
    value - the position of that plane along the chosen axis,
    i.e. the axis offset of the dividing plane.
    If type == 4 (Y) and value == 100.0,
    the plane is y = 100. To decide which side a point falls on,
    you read the point's coordinate at the axis given by type and compare
    it against value: less goes to the negative/left subtree, greater-or-equal goes
    to the positive/right subtree. For an axis-aligned plane this comparison is the
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

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_PlaneSector_Struct":
        ps_s = RW_PlaneSector_Struct()
        ps_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            ps_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_PlaneSector_Struct chunk type",
        )

        ps_s.type = RW_PlaneSector_Type(parser.readUint32())

        ps_s.value = parser.readFloat()

        ps_s.left_is_atomic = parser.readUint32()
        ps_s.right_is_atomic = parser.readUint32()

        ps_s.left_value = parser.readFloat()
        ps_s.right_value = parser.readFloat()

        return ps_s

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        _write_u32(buf, this.type.value)
        _write_f32(buf, this.value)
        _write_u32(buf, this.left_is_atomic)
        _write_u32(buf, this.right_is_atomic)
        _write_f32(buf, this.left_value)
        _write_f32(buf, this.right_value)

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

    left_child: Union["RW_PlaneSector", RW_AtomicSector] = (
        None  # can be either a plane sector or an atomic sector
    )
    right_child: Union["RW_PlaneSector", RW_AtomicSector] = (
        None  # can be either a plane sector or an atomic sector
    )

    # kept so children can resolve worldFlags from their parent; hidden from
    # repr to avoid repeating the flags at every tree node
    worldFlags: RpWorldFlags = field(default=None, repr=False)

    @staticmethod
    def read(parser: Parser, parent=None, worldFlags: RpWorldFlags=None) -> "RW_PlaneSector":
        ps = RW_PlaneSector()
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

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        this.struct.write(buf, stamp, parent=this)

        this.left_child.write(buf, stamp, parent=this)
        this.right_child.write(buf, stamp, parent=this)

        rw_header = RWHeader(
            type=RWSectionType.rwID_PLANESECT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    def collect_atomic_sectors(
        this,
    ) -> list[RW_AtomicSector]:
        sectors = []

        if isinstance(this.left_child, RW_AtomicSector):
            sectors.append(this.left_child)
        elif isinstance(this.left_child, RW_PlaneSector):
            sectors.extend(this.left_child.collect_atomic_sectors())

            
        if isinstance(this.right_child, RW_AtomicSector):
            sectors.append(this.right_child)
        elif isinstance(this.right_child, RW_PlaneSector):
            sectors.extend(this.right_child.collect_atomic_sectors())

        return sectors
