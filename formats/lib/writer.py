import struct


def _write_u8(f, v):
    f.write(struct.pack("<B", v))


def _write_u16(f, v):
    f.write(struct.pack("<H", v))


def _write_u32(f, v):
    f.write(struct.pack("<I", v))

def _write_bool(f, v):
    f.write(struct.pack("<i", int(v)))  # Write as 4-byte signed int

def _write_s32(f, v):
    f.write(struct.pack("<i", v))


def _write_f32(f, v):
    f.write(struct.pack("<f", v))

def _write_f16(f, v):
    f.write(struct.pack("<e", v))


def _write_fixedString(f, content="", size=32):
    if len(content) > size:
        raise ValueError(f"Content length {len(content)} exceeds fixed size {size}")
    
    encoded = content.encode("latin-1", errors="replace")
    padded = encoded + b"\x00" * (size - len(encoded))

    f.write(padded)

def _write_lengthPrefixedString(f, content="", addNullTerminator=True, alignTo4=False):
    encoded = content.encode("latin-1", errors="replace") + (b"\x00" if addNullTerminator else b"")

    length = len(encoded)

    if alignTo4:
        padding_length = (4 - (length % 4)) % 4
        encoded += b"\xBF" * padding_length
        length += padding_length

    f.write(struct.pack("<I", length)) # uint32
    f.write(encoded)

def _write_alignedString(f, content="", alignment=4, padding_byte=b"\xBF"):
    encoded = content.encode("latin-1", errors="replace") + b"\x00"  # Null-terminated
    padding_length = (alignment - (len(encoded) % alignment)) % alignment
    padded = encoded + padding_byte * padding_length

    f.write(padded)

def _write_guid(f, guid):
    if isinstance(guid, str):
        import uuid
        guid = uuid.UUID(guid)
    f.write(guid.bytes_le)
