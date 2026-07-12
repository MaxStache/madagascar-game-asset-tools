import io
from dataclasses import dataclass, field

from formats.lib.writer import _write_u32
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from formats.sections.EXTENSION_0003 import RW_Extension

@dataclass
class RpAtomicFlags:
    # https://gtamods.com/wiki/Atomic_(RW_Section)
    collision_test: bool = (
        False  # 0x00000001 — Include this atomic in RenderWare's collision system.
    )
    render: bool = False  # 0x00000004 — Render this atomic when it is inside the camera's view frustum. Almost every visible model has this enabled.

    @staticmethod
    def decode(value: int) -> "RpAtomicFlags":
        f = RpAtomicFlags()

        f.collision_test = bool(value & 0x00000001)
        f.render = bool(value & 0x00000004)

        return f

    def encode(self) -> int:
        v = 0

        if self.collision_test:
            v |= 0x00000001
        if self.render:
            v |= 0x00000004

        return v

    def print(self):
        print("RpAtomicFlags:")
        print(f"  collision_test: {self.collision_test}")
        print(f"  render: {self.render}")


@dataclass
class RW_Atomic_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    frame_index: int = 0  # u32
    geometry_index: int = 0  # u32
    flags: RpAtomicFlags = field(default_factory=RpAtomicFlags)
    unused: int = 0  # u32

    @staticmethod
    def read(parser: Parser) -> "RW_Atomic_Struct":
        atomic_s = RW_Atomic_Struct()
        atomic_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            atomic_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_Atomic_Struct chunk type",
        )

        atomic_s.frame_index = parser.readUint32()
        atomic_s.geometry_index = parser.readUint32()
        atomic_s.flags = RpAtomicFlags.decode(parser.readUint32())
        atomic_s.unused = parser.readUint32()

        return atomic_s

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        _write_u32(buf, this.frame_index)  # frame_index
        _write_u32(buf, this.geometry_index)  # geometry_index
        _write_u32(buf, this.flags.encode())  # flags
        _write_u32(buf, this.unused)  # unused

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

@dataclass
class RW_Atomic(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_Atomic_Struct = field(default_factory=RW_Atomic_Struct)

    extension: RW_Extension = field(default_factory=RW_Extension)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_Atomic":
        atomic = RW_Atomic()
        atomic.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            atomic.header,
            RWSectionType.rwID_ATOMIC.value,
            "RW_Atomic chunk type",
        )

        atomic.struct = RW_Atomic_Struct.read(parser)

        atomic.extension = RW_Extension.read(parser, parent=atomic)

        return atomic

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        this.struct.write(buf, stamp, parent=this)

        this.extension.write(buf, stamp, parent=this)

        rw_header = RWHeader(
            type=RWSectionType.rwID_ATOMIC.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
