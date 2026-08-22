import io
from dataclasses import dataclass, field
from typing import override

from madagascar.lib.writer import write_u32
from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise, RW_Frame

from madagascar.sections.EXTENSION_0003 import RW_Extension

@dataclass
class RW_FrameList_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    frame_count: int = 0  # u32
    frames: list[RW_Frame] = field(default_factory=list)  # RW_Frame each

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_FrameList_Struct":
        fl_struct = cls()
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

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u32(buf, len(self.frames))  # frame_count
        for frame in self.frames:
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

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_FrameList":
        framelist = cls()
        framelist.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            framelist.header,
            RWSectionType.rwID_FRAMELIST.value,
            "RW_FrameList chunk type",
        )

        section_end = parser.tell() + framelist.header.size

        framelist.struct = RW_FrameList_Struct.read(parser)

        while parser.tell() < section_end:
            extension = RW_Extension.read(parser, parent=framelist)
            framelist.extensions.append(extension)

        if parser.tell() != section_end:
            raise ValueError(
                f"RW_FrameList parsing ended at offset {parser.tell()}, expected {section_end}"
            )

        return framelist

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        self.struct.write(buf, stamp)

        for extension in self.extensions:
            extension.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_FRAMELIST.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
