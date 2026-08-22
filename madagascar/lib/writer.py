import struct
from typing import BinaryIO
import uuid


def write_u8(f: BinaryIO, v: int):
    f.write(struct.pack("<B", v))


def write_u16(f: BinaryIO, v: int):
    f.write(struct.pack("<H", v))


def write_u32(f: BinaryIO, v: int):
    f.write(struct.pack("<I", v))

def write_bool(f: BinaryIO, v: bool):
    f.write(struct.pack("<i", int(v)))  # Write as 4-byte signed int

def write_s32(f: BinaryIO, v: int):
    f.write(struct.pack("<i", v))


def write_f32(f: BinaryIO, v: float):
    f.write(struct.pack("<f", v))

def write_f16(f: BinaryIO, v: float):
    f.write(struct.pack("<e", v))


def write_fixedString(f: BinaryIO, content="", size=32):
    if len(content) > size:
        raise ValueError(f"Content length {len(content)} exceeds fixed size {size}")
    
    encoded = content.encode("latin-1", errors="replace")
    padded = encoded + b"\x00" * (size - len(encoded))

    f.write(padded)

def write_lengthPrefixedString(f: BinaryIO, content="", addNullTerminator=True, alignTo4=False):
    encoded = content.encode("latin-1", errors="replace") + (b"\x00" if addNullTerminator else b"")

    length = len(encoded)

    if alignTo4:
        padding_length = (4 - (length % 4)) % 4
        encoded += b"\xBF" * padding_length
        length += padding_length

    f.write(struct.pack("<I", length)) # uint32
    f.write(encoded)

def write_alignedString(f: BinaryIO, content="", alignment=4, padding_byte=b"\xBF"):
    encoded = content.encode("latin-1", errors="replace") + b"\x00"  # Null-terminated
    padding_length = (alignment - (len(encoded) % alignment)) % alignment
    padded = encoded + padding_byte * padding_length

    f.write(padded)

def write_guid(f: BinaryIO, guid: uuid.UUID):
    if isinstance(guid, str):
        import uuid
        guid = uuid.UUID(guid)
    f.write(guid.bytes_le)
