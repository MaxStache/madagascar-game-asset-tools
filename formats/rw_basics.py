import struct
from dataclasses import dataclass, field
from rwConstants import RWSectionType
from lib.parser import Parser


def _write_u8(f, v):
    f.write(struct.pack("<B", v))


def _write_u16(f, v):
    f.write(struct.pack("<H", v))


def _write_u32(f, v):
    f.write(struct.pack("<I", v))


def _write_s32(f, v):
    f.write(struct.pack("<i", v))


def _write_f32(f, v):
    f.write(struct.pack("<f", v))


def _write_bytes(f, data):
    f.write(data)


def _read_fixed_string(f, length: int) -> str:
    raw = f.read(length)
    null = raw.find(b"\x00")
    return (raw[:null] if null >= 0 else raw).decode("ascii", errors="replace")


def _write_fixed_string(f, s: str, length: int):
    encoded = s.encode("ascii", errors="replace")[: length - 1]
    f.write(encoded + b"\x00" * (length - len(encoded)))


def _write_header(f, chunk_type: int, size: int, stamp: int = None):
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

    libid &= 0xFFFFFFFF  # treat as RwUInt32

    if libid & 0xFFFF0000:
        version = ((libid >> 14) & 0x3FF00) + 0x30000 | ((libid >> 16) & 0x3F)
        build = libid & 0xFFFF
    else:
        version = libid << 8
        build = 0

    return version, build


def versionHex_to_string(value):
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
    library_id_stamp: int = None

    BYTE_SIZE = 4 * 3  # 3 * 4 bytes

    @property
    def binSize(self):
        return 4 * 3  # 3 * 4 bytes

    def pack(self) -> bytes:
        return struct.pack("<III", self.type, self.size, self.library_id_stamp)

    @staticmethod
    def read(parser: Parser) -> "RWHeader":
        read_header = parser.readRWChunkHeader()
        return RWHeader(
            type=read_header["id"],
            size=read_header["size"],
            library_id_stamp=read_header["version"],
        )

    @property
    def version(self) -> str:
        version, build = library_id_unpack(self.library_id_stamp)
        return version

    @property
    def version_string(self) -> str:
        version, build = library_id_unpack(self.library_id_stamp)
        version_str = versionHex_to_string(version)
        return version_str

    @property
    def build(self) -> str:
        version, build = library_id_unpack(self.library_id_stamp)
        return build
    
    def print(self):
        print(self.__repr__())

    def __repr__(self):
        return f"RWHeader(type={hex(self.type)}, size={self.size}, library_id_stamp={hex(self.library_id_stamp)}, version={hex(self.version)}, build={self.build})"


@dataclass(frozen=True, slots=True)
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @staticmethod
    def read(parser: Parser) -> "Vector3":
        return Vector3(
            x=parser.readFloat(),
            y=parser.readFloat(),
            z=parser.readFloat(),
        )

    def write(this, f):
        _write_f32(f, this.x)
        _write_f32(f, this.y)
        _write_f32(f, this.z)


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

    def write(this, f):
        _write_u8(f, this.r)
        _write_u8(f, this.g)
        _write_u8(f, this.b)
        _write_u8(f, this.a)


@dataclass()
class RWSphere:
    location: Vector3 = field(default_factory=Vector3)
    radius: float = 0.0

    @staticmethod
    def read(parser: Parser) -> "RWSphere":
        return RWSphere(location=Vector3.read(parser), radius=parser.readFloat())

    def write(this, f):
        this.location.write(f)
        _write_f32(f, this.radius)


def expect_chunk_type_or_raise(
    header: RWHeader, expected_type: int, error: str = "Wrong Chunk Type"
):
    if header.type != expected_type:
        raise ValueError(
            f"{error}: expected 0x{expected_type:02X}, got 0x{header.type:02X} ({int(header.type)})"
        )


@dataclass
class RW_Section:
    @staticmethod
    def read(parser: Parser) -> "RW_Section":
        raise NotImplementedError("[read] This section type is not implemented yet.")

    @staticmethod
    def write(this, f, stamp):
        raise NotImplementedError("[write] This section type is not implemented yet.")


@dataclass
class RW_Section_NotImplemented(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    raw_data: bytes = b""  # header.payload_size

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_Section_NotImplemented":
        sni = RW_Section_NotImplemented(RWHeader.read(parser))

        sni.raw_data = parser.readBytes(sni.header.size)

        return sni

    @staticmethod
    def write(this, f, stamp):
        rw_header = RWHeader(
            type=this.header.type,
            size=len(this.raw_data),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(this.raw_data)

    def __init__(self, header):
        self.header = header

        try:
            secname = RWSectionType(self.header.type).name
        except ValueError:
            secname = "Unknown"

        print(
            "\033[93m"
            "======================= Warning =======================\n"
            "Section parser not implemented. (or mapped)\n"
            f" Type : {self.header.type:#06x} ({secname})\n"
            "\n"
            " Data will be preserved:\n"
            "   • header -> self.header\n"
            "   • payload -> self.raw_data\n"
            "\n"
            " To add support, create a parser in formats/sections.\n",
            "(or add existing one to \n       formats/sections/__init__.py - SECTION_REGISTRY)\n"
            "\033[0m"
        )