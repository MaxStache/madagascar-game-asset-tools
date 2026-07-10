import io
from dataclasses import dataclass, field

from ..lib.writer import _write_u32, _write_s32
from ..lib.parser import Parser
from ..rwConstants import RWSectionType
from ..rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise, Vector3, RW_Matrix3x3

from .EXTENSION_0003 import RW_Extension

@dataclass
class RW_Frame:
    """https://gtamods.com/wiki/Frame_List_(RW_Section)"""
    rotation_matrix: RW_Matrix3x3 = field(default_factory=RW_Matrix3x3)
    position: Vector3 = field(default_factory=Vector3)
    parent_idx: int = -1  # s32
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
class RW_FrameList_Struct(RW_Section):
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
class RW_FrameList(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_FrameList_Struct = field(default_factory=RW_FrameList_Struct)

    extensions: list[RW_Extension] = field(default_factory=list)

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
            extension = RW_Extension.read(parser)
            framelist.extensions.append(extension)

        if parser.tell() != section_end:
            raise ValueError(
                f"RW_FrameList parsing ended at offset {parser.tell()}, expected {section_end}"
            )

        return framelist

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)

        for extension in this.extensions:
            extension.write(buf, stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_FRAMELIST.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
