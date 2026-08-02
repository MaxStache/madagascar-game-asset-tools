import struct
from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from formats.lib.rwConstants import DEFAULT_VERSION_STAMP, strfunc_func

try:
    from lib.parser import Parser

    from formats.lib.rwConstants import RWSectionType
except ImportError:
    from formats.lib.parser import Parser
    from formats.lib.rwConstants import RWSectionType


def write_u8(f: BinaryIO, v: int):
    f.write(struct.pack("<B", v))


def write_u16(f: BinaryIO, v: int): # type: ignore
    f.write(struct.pack("<H", v))


def write_u32(f: BinaryIO, v: int):
    f.write(struct.pack("<I", v))


def write_s32(f: BinaryIO, v: int):
    f.write(struct.pack("<i", v))


def write_f32(f: BinaryIO, v: float):
    f.write(struct.pack("<f", v))


def write_bytes(f: BinaryIO, data: bytes): # type: ignore
    f.write(data)


def _read_fixed_string(f: BinaryIO, length: int) -> str: # type: ignore
    raw = f.read(length)
    null = raw.find(b"\x00")
    return (raw[:null] if null >= 0 else raw).decode("ascii", errors="replace")


def _write_fixed_string(f: BinaryIO, s: str, length: int): # type: ignore
    encoded = s.encode("ascii", errors="replace")[: length - 1]
    f.write(encoded + b"\x00" * (length - len(encoded)))


def _write_header(f: BinaryIO, chunk_type: int, size: int, stamp: int): # type: ignore
    f.write(struct.pack("<III", chunk_type, size, stamp))


@dataclass
class RW_Triangle:
    vertex1: int = 0  # uint16
    vertex2: int = 0  # uint16
    vertex3: int = 0  # uint16
    materialIndex: int = 0  # uint16


@dataclass
class RW_GeometryTriangle:
    vertex2: int = 0  # uint16
    vertex1: int = 0  # uint16
    materialIndex: int = 0  # uint16
    vertex3: int = 0  # uint16


def library_id_unpack(libid: int) -> tuple[int, int]:
    """
    Unpack a RenderWare library ID stamp.

    Returns:
        (version, build)
        version is encoded as 0xVJNBB (e.g. 0x36003 = 3.6.0.3)
        build is a 16-bit build number

    version is encoded as follows:
        V: Major version
        J: Minor version
        N: Patch version
        BB: Binary revision

        -> For example, 0x36003 would be version 3.6.0.03 when V.J.N.BB

    """

    #if libid is None:
    #    return 0, 0

    libid &= 0xFFFFFFFF  # treat as RwUInt32

    if libid & 0xFFFF0000:
        version = ((libid >> 14) & 0x3FF00) + 0x30000 | ((libid >> 16) & 0x3F)
        build = libid & 0xFFFF
    else:
        version = libid << 8
        build = 0

    return version, build


def versionHex_to_string(value: int) -> str:
    h = f"{value:X}"

    major = h[0]
    minor = h[1]
    revision = h[2:-2] or "0"
    build = h[-2:]

    return f"{int(major, 16)}.{int(minor, 16)}.{int(revision, 16)}.{int(build, 16):02}"


@dataclass
class RWHeader:
    type: int = 0
    size: int = 0
    library_id_stamp: int = DEFAULT_VERSION_STAMP

    BYTE_SIZE = 4 * 3  # 3 * 4 bytes

    @property
    def binSize(self):
        return 4 * 3  # 3 * 4 bytes

    def pack(self) -> bytes:
        return struct.pack("<III", self.type, self.size, self.library_id_stamp)

    @staticmethod
    def read(parser: Parser) -> "RWHeader":
        read_header = parser.readRWChunkHeader()
        # print(f"Read RWHeader: type=0x{read_header['id']:X}, size={read_header['size']}, version=0x{read_header['version']:X}")
        return RWHeader(
            type=read_header["id"],
            size=read_header["size"],
            library_id_stamp=read_header["version"],
        )

    @staticmethod
    def from_dict(content: dict[str, Any]) -> "RWHeader":
        return RWHeader(
            type=content.get("type", 0),
            size=content.get("size", 0),
            library_id_stamp=content.get("library_id_stamp", DEFAULT_VERSION_STAMP),
        )
    
    @staticmethod
    def peek(parser: Parser) -> "RWHeader":
        read_header = parser.peekRWChunkHeader()
        return RWHeader(
            type=read_header["id"],
            size=read_header["size"],
            library_id_stamp=read_header["version"],
        )

    @property
    def version(self) -> int:
        version, _build = library_id_unpack(self.library_id_stamp)
        return version

    @property
    def version_string(self) -> str:
        version, _build = library_id_unpack(self.library_id_stamp)
        version_str = versionHex_to_string(version)
        return version_str

    @property
    def build(self) -> int:
        _version, build = library_id_unpack(self.library_id_stamp)
        return build

    def print(self):
        print(self.__repr__())

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "size": self.size,
            "library_id_stamp": self.library_id_stamp,
        }

    @override
    def __repr__(self):
        return f"RWHeader(type={hex(self.type)}, size={self.size}, library_id_stamp={hex(self.library_id_stamp if self.library_id_stamp else 0)}, version={hex(self.version)}, build={self.build})"


@dataclass(frozen=True, slots=True)
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def read(cls, parser: Parser) -> "Vector3":
        return cls(
            x=parser.readFloat(),
            y=parser.readFloat(),
            z=parser.readFloat(),
        )

    def write(self, f: BinaryIO):
        write_f32(f, self.x)
        write_f32(f, self.y)
        write_f32(f, self.z)

@dataclass(frozen=True, slots=True)
class Vector4:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 0.0

    @classmethod
    def read(cls, parser: Parser) -> "Vector4":
        return cls(
            x=parser.readFloat(),
            y=parser.readFloat(),
            z=parser.readFloat(),
            w=parser.readFloat(),
        )

    def write(self, f: BinaryIO):
        write_f32(f, self.x)
        write_f32(f, self.y)
        write_f32(f, self.z)
        write_f32(f, self.w)


@dataclass()
class RWColor32:
    r: int = 0  # u8
    g: int = 0  # u8
    b: int = 0  # u8
    a: int = 0  # u8

    @staticmethod
    def read(parser: Parser) -> "RWColor32":
        return RWColor32(
            r=parser.readUint8(),
            g=parser.readUint8(),
            b=parser.readUint8(),
            a=parser.readUint8(),
        )

    def write(self, f: BinaryIO):
        write_u8(f, self.r)
        write_u8(f, self.g)
        write_u8(f, self.b)
        write_u8(f, self.a)


@dataclass()
class RWSphere:
    location: Vector3 = field(default_factory=Vector3)
    radius: float = 0.0

    @staticmethod
    def read(parser: Parser) -> "RWSphere":
        return RWSphere(location=Vector3.read(parser), radius=parser.readFloat())

    def write(self, f: BinaryIO):
        self.location.write(f)
        write_f32(f, self.radius)


@dataclass
class RW_UV:
    u: float = 0.0
    v: float = 0.0


class RW_Vector2:
    x: float = 0.0
    y: float = 0.0


@dataclass
class RW_Matrix2x3:
    row1: Vector3 = field(default_factory=Vector3)
    row2: Vector3 = field(default_factory=Vector3)

    def write(self, f: BinaryIO):
        self.row1.write(f)
        self.row2.write(f)

    @classmethod
    def read(cls, parser: Parser) -> "RW_Matrix2x3":
        return cls(
            row1=Vector3.read(parser),
            row2=Vector3.read(parser),
        )


@dataclass
class RW_Matrix3x3:
    row1: Vector3 = field(default_factory=Vector3)
    row2: Vector3 = field(default_factory=Vector3)
    row3: Vector3 = field(default_factory=Vector3)

    def write(self, f: BinaryIO):
        self.row1.write(f)
        self.row2.write(f)
        self.row3.write(f)

    @classmethod
    def read(cls, parser: Parser) -> "RW_Matrix3x3":
        return cls(
            row1=Vector3.read(parser),
            row2=Vector3.read(parser),
            row3=Vector3.read(parser),
        )

    @override
    def __repr__(self):
        return f"RW_Matrix3x3({self.row1}, {self.row2}, {self.row3})"


@dataclass
class RW_Matrix4x4:
    row1: Vector4 = field(default_factory=Vector4)
    row2: Vector4 = field(default_factory=Vector4)
    row3: Vector4 = field(default_factory=Vector4)
    row4: Vector4 = field(default_factory=Vector4)

    def write(self, f: BinaryIO):
        self.row1.write(f)
        self.row2.write(f)
        self.row3.write(f)
        self.row4.write(f)

    @classmethod
    def read(cls, parser: Parser) -> "RW_Matrix4x4":
        row1 = Vector4.read(parser)
        row2 = Vector4.read(parser)
        row3 = Vector4.read(parser)
        row4 = Vector4.read(parser)
        return cls(row1=row1, row2=row2, row3=row3, row4=row4)

    def get_translation(self) -> Vector3:
        """Get the translation component of the matrix (row4, x,y,z)."""
        return Vector3(x=self.row4.x, y=self.row4.y, z=self.row4.z)

    @override
    def __repr__(self):
        return f"RW_Matrix4x4(\n{self.row1},\n {self.row2},\n {self.row3},\n {self.row4})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "row1": {"x": self.row1.x, "y": self.row1.y, "z": self.row1.z, "w": self.row1.w},
            "row2": {"x": self.row2.x, "y": self.row2.y, "z": self.row2.z, "w": self.row2.w},
            "row3": {"x": self.row3.x, "y": self.row3.y, "z": self.row3.z, "w": self.row3.w},
            "row4": {"x": self.row4.x, "y": self.row4.y, "z": self.row4.z, "w": self.row4.w},
        }

    @staticmethod
    def from_dict(content: dict[str, Any]) -> "RW_Matrix4x4":
        row1 = content.get("row1", {})
        row2 = content.get("row2", {})
        row3 = content.get("row3", {})
        row4 = content.get("row4", {})

        return RW_Matrix4x4(
            row1=Vector4(
                x=row1.get("x", 0.0),
                y=row1.get("y", 0.0),
                z=row1.get("z", 0.0),
                w=row1.get("w", 0.0),
            ),
            row2=Vector4(
                x=row2.get("x", 0.0),
                y=row2.get("y", 0.0),
                z=row2.get("z", 0.0),
                w=row2.get("w", 0.0),
            ),
            row3=Vector4(
                x=row3.get("x", 0.0),
                y=row3.get("y", 0.0),
                z=row3.get("z", 0.0),
                w=row3.get("w", 0.0),
            ),
            row4=Vector4(
                x=row4.get("x", 0.0),
                y=row4.get("y", 0.0),
                z=row4.get("z", 0.0),
                w=row4.get("w", 0.0),
            ),
        )

def expect_chunk_type_or_raise(
    header: RWHeader, expected_type: int, error: str = "Wrong Chunk Type"
):
    if header.type != expected_type:
        raise ValueError(
            f"{error}: expected 0x{expected_type:02X}, got 0x{header.type:02X} ({int(header.type)})"
        )


@dataclass
class RW_Section:
    header: RWHeader = field(default_factory=RWHeader)
    
    @classmethod
    def read(cls, parser: Parser, parent: "RW_Section | None" = None) -> "RW_Section":
        raise NotImplementedError("[read] This section type is not implemented yet.")

    def write(self, f: BinaryIO, stamp: int, parent: "RW_Section | None" = None) -> None:
        raise NotImplementedError("[write] This section type is not implemented yet.")


@dataclass
class RW_Section_NotImplemented(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    raw_data: bytes = b""  # header.payload_size

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_Section_NotImplemented":
        sni = cls(RWHeader.read(parser))

        sni.raw_data = parser.readBytes(sni.header.size)

        return sni

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        rw_header = RWHeader(
            type=self.header.type,
            size=len(self.raw_data),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(self.raw_data)

    @override
    def __repr__(self):
        output = f"RW_Section_NotImplemented(type={hex(self.header.type)}, size={self.header.size}, library_id_stamp={hex(self.header.library_id_stamp if self.header.library_id_stamp else 0)}, version={hex(self.header.version)}, build={self.header.build})"

        output += f"\n# raw_data: {len(self.raw_data)} bytes"

        if self.header.type == 0x1:
            output += "\n# This is a struct, parsing is implemented on parent"

        return output 

    def __init__(self, header: RWHeader):
        self.header = header

        try:
            secname = RWSectionType(self.header.type).name
        except ValueError:
            secname = "Unknown"

        print(
            "\033[93m"
            + "======================= Warning =======================\n"
            + "Section parser not implemented. (or mapped)\n"
            + f" Type : {self.header.type:#06x} ({secname})\n"
            + "\n"
            + " Data will be preserved:\n"
            + "   • header -> self.header\n"
            + "   • payload -> self.raw_data\n"
            + "\n"
            + " To add support, create a parser in formats/sections.\n"
            + "(or add existing one to \n       formats/sections/__init__.py - SECTION_REGISTRY)\n"
            + "\033[0m",
        )

@dataclass
class RW_StreamFunc:
    @classmethod
    def read(cls, parser: Parser) -> "RW_StreamFunc":
        raise NotImplementedError("[read] This string func type is not implemented yet.")

    def write(self, f: BinaryIO, stamp: int) -> None:
        raise NotImplementedError("[write] This string func type is not implemented yet.")

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError("[to_dict] This string func type is not implemented yet.")

    @classmethod
    def from_dict(cls, content: dict[str, Any]) -> "RW_StreamFunc":
        raise NotImplementedError("[from_dict] This string func type is not implemented yet.")


    @property
    def streamfunc(self) -> strfunc_func | None:
        return None
@dataclass
class RW_StreamFunc_NotImplemented(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    raw_data: bytes = field(default_factory=bytes)  # header.payload_size

    @classmethod
    @override
    def read(cls, parser: Parser) -> "RW_StreamFunc_NotImplemented":
        sni = cls(RWHeader.read(parser))

        sni.raw_data = parser.readBytes(sni.header.size)

        return sni

    @override
    def write(self, f: BinaryIO, stamp: int):
        rw_header = RWHeader(
            type=self.header.type,
            size=len(self.raw_data),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(self.raw_data)


    def __init__(self, header: RWHeader, raw_data: bytes = b""):
        self.header = header
        self.raw_data = raw_data

        try:
            secname = RWSectionType(self.header.type).name
        except ValueError:
            secname = "Unknown"

        print(
            "\033[93m"
            + "======================= Warning =======================\n"
            + "StrFunc parser not implemented. (or mapped)\n"
            + f" Type : {self.header.type:#06x} ({secname})\n"
            + "\033[0m",
        )

    @property
    @override
    def streamfunc(self):
        return strfunc_func(self.header.type)


    @override
    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "raw_data": self.raw_data.hex(),
        }

    @classmethod
    @override
    def from_dict(cls, content: dict[str, Any]) -> "RW_StreamFunc":
        raw_data_hex = content.get("raw_data", "")

        header = RWHeader.from_dict(content.get("header", {}))

        raw_data = bytes.fromhex(raw_data_hex)

        return cls(header=header, raw_data=raw_data)
    
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

    def write(self, f: BinaryIO):
        self.rotation_matrix.write(f)
        self.position.write(f)
        write_s32(f, self.parent_idx)
        write_u32(f, self.matrix_flags)