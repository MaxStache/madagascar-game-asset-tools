from enum import Enum
import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union, Optional
from lib.parser import Parser
from rwConstants import RWSectionType, RWSectionType_TFB, DEFAULT_VERSION_STAMP


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
class RW_World_Triangle:
    vertex1: int = 0  # uint16
    vertex2: int = 0  # uint16
    vertex3: int = 0  # uint16
    materialIndex: int = 0  # uint16


@dataclass
class RWHeader:
    type: int = 0
    size: int = 0
    library_id_stamp: int = None

    @property
    def binSize(self):
        return 4 * 3  # 3 uint32 fields

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
        if self.library_id_stamp & 0xFFFF0000:
            v = (self.library_id_stamp >> 14 & 0x3FF00) + 0x30000
            v |= self.library_id_stamp >> 16 & 0x3F
            return f"{(v >> 16) & 0xF}.{(v >> 12) & 0xF}.{(v >> 8) & 0xF}.{v & 0xFF}"
        return "3.1.0.0"


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
