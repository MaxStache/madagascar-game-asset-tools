import io
from dataclasses import dataclass, field

from formats.lib.writer import _write_u32
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from formats.sections.EXTENSION_0003 import RW_Extension
from formats.sections.ATOMIC_0014 import RW_Atomic
from formats.sections.FRAMELIST_000E import RW_FrameList
from formats.sections.GEOMETRYLIST_001A import RW_GeometryList
from formats.sections.CAMERA_0005 import RW_Camera


@dataclass
class RW_Clump_Struct:
    header: RWHeader = field(default_factory=RWHeader)

    numAtomics: int = 0  # u32
    numLights: int = 0  # u32 - only present after version 0x33000
    numCameras: int = 0  # u32 - only present after version 0x33000

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_Clump_Struct":
        clump_s = RW_Clump_Struct()
        clump_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            clump_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_Clump_Struct chunk type",
        )

        clump_s.numAtomics = parser.readUint32()
        clump_s.numLights = parser.readUint32()
        clump_s.numCameras = parser.readUint32()

        return clump_s

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
class RW_Clump(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: "RW_Clump_Struct" = field(default_factory=RW_Clump_Struct)

    frame_list: RW_FrameList = field(default_factory=RW_FrameList)
    geometry_list: RW_GeometryList = field(default_factory=RW_GeometryList)

    atomics: list[RW_Atomic] = field(default_factory=list)

    camera_frame_indices: list[int] = field(default_factory=list)  # u32 each numCameras
    cameras: list[RW_Camera] = field(default_factory=list)
    
    extension: RW_Extension = field(default_factory=RW_Extension)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_Clump":
        clump = RW_Clump()
        clump.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            clump.header,
            RWSectionType.rwID_CLUMP.value,
            "RW_Clump chunk type",
        )

        # Frame List
        # ===================
        clump.struct = RW_Clump_Struct.read(parser)

        # Frame List
        # ===================
        clump.frame_list = RW_FrameList.read(parser)

        # Frame List
        # ===================
        clump.geometry_list = RW_GeometryList.read(parser)

        # Atomics follow the geometry list in DFF clumps
        clump.atomics = []
        for _ in range(clump.struct.numAtomics):
            clump.atomics.append(RW_Atomic.read(parser))

        if clump.struct.numLights > 0:
            raise NotImplementedError(
                f"RW_Clump has {clump.struct.numLights} lights, but light parsing is not implemented"
            )
        
        for _ in range(clump.struct.numCameras):
            parser.readRWChunkHeader()  # skip
            clump.camera_frame_indices.append(parser.readUint32())
            clump.cameras.append(RW_Camera.read(parser))

        clump.extension = RW_Extension.read(parser, parent=clump)

        return clump

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)

        this.frame_list.write(buf, stamp, parent=this)

        this.geometry_list.write(buf, stamp, parent=this)

        for atomic in this.atomics:
            atomic.write(buf, stamp, parent=this)

        for cam in range(this.struct.numCameras):
            _write_u32(buf, this.camera_frame_indices[cam])
            this.cameras[cam].write(buf, stamp, parent=this)

        this.extension.write(buf, stamp, parent=this)

        rw_header = RWHeader(
            type=RWSectionType.rwID_CLUMP.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())