import struct
from typing import Any
import uuid


class Parser:
    def __init__(self, data: bytes, endian: str = "little"):
        self.data = data
        self.offset = 0

        if endian == "little":
            self.endian = "<"
        elif endian == "big":
            self.endian = ">"
        else:
            raise ValueError("endian must be 'little' or 'big'")

    # -------------------------
    # Core helpers
    # -------------------------

    def _read(self, fmt: str) -> Any:
        size = struct.calcsize(fmt)
        if self.offset + size > len(self.data):
            raise EOFError("Attempt to read past end of buffer")
    
        value = struct.unpack_from(fmt, self.data, self.offset)[0]
        self.offset += size
        return value
    
    def _readTuple(self, fmt: str) -> tuple[Any, ...]:
        size = struct.calcsize(fmt)
        if self.offset + size > len(self.data):
            raise EOFError("Attempt to read past end of buffer")

        value = struct.unpack_from(fmt, self.data, self.offset)
        self.offset += size
        return value

    def read(self, size: int) -> bytes:
        """
        Equivalent to RwStreamRead(stream, buffer, size)
        Returns bytes read (may be shorter only at EOF).
        """
        if self.offset + size > len(self.data):
            return b""

        chunk = self.data[self.offset : self.offset + size]
        self.offset += size
        return chunk

    def seek(self, offset: int):
        if offset < 0 or offset > len(self.data):
            raise ValueError("Invalid seek offset")
        self.offset = offset

    def tell(self) -> int:
        return self.offset

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def readRemaining(self) -> bytes:
        return self.read(self.remaining())

    def skip(self, size: int):
        self.seek(self.offset + size)

    def canRead(self, size: int) -> bool:
        return self.offset + size <= len(self.data)

    def getRemainingBytes(self) -> int:
        return len(self.data) - self.offset

    # -------------------------
    # Integer reads
    # -------------------------

    def readUint8(self) -> int:
        return self._read(self.endian + "B")

    def readInt8(self):
        return self._read(self.endian + "b")

    def readUint16(self):
        return self._read(self.endian + "H")

    def readInt16(self):
        return self._read(self.endian + "h")

    def readUint32(self):
        return self._read(self.endian + "I")

    def peekUint32(self):
        if self.offset + 4 > len(self.data):
            raise EOFError("Attempt to read past end of buffer")
        return struct.unpack_from(self.endian + "I", self.data, self.offset)[0]

    def readInt32(self):
        return self._read(self.endian + "i")

    def readUint64(self):
        return self._read(self.endian + "Q")

    def readInt64(self):
        return self._read(self.endian + "q")

    # -------------------------
    # Floating point
    # -------------------------

    def readFloat(self):
        return self._read(self.endian + "f")

    def readFloat16(self):
        return self._read(self.endian + "e")

    def readDouble(self):
        return self._read(self.endian + "d")

    # -------------------------
    # Raw / strings
    # -------------------------

    def readBytes(self, size: int) -> bytes:
        if self.offset + size > len(self.data):
            raise EOFError("Attempt to read past end of buffer")

        b = self.data[self.offset : self.offset + size]
        self.offset += size
        return b

    def readCString(self, encoding="latin-1") -> str:
        start = self.offset
        while self.offset < len(self.data) and self.data[self.offset] != 0:
            self.offset += 1

        if self.offset >= len(self.data):
            raise EOFError("Unterminated C string")

        s = self.data[start : self.offset].decode(encoding)
        self.offset += 1  # skip null byte
        return s

    def readPaddedCString(self, alignment=4, encoding="latin-1") -> str:
        start = self.offset
        s = self.readCString(encoding)
        byte_length = self.offset - start  # actual bytes consumed including null
        remainder = byte_length % alignment
        if remainder:
            self.offset += alignment - remainder
        return s

    def readString(self, length: int, encoding="latin-1") -> str:
        b = self.readBytes(length)
        return b.decode(encoding)

    def readLengthPrefixedString(self, encoding="latin-1", removePadding=False) -> str:
        # u32 length prefix
        # char[length]
        # non-null-terminated, but may be padded to 4 bytes
        length = self.readUint32()
        b = self.readBytes(length)
        
        if removePadding:
            # Remove null padding at the end
            b = b.rstrip(b"\x00")
            b = b.rstrip(b"\xbf")
            b = b.rstrip(b"\x00")
            
        return b.decode(encoding)

    def readGUID(self):
        guid_bytes = self.readBytes(16)
        return uuid.UUID(bytes_le=guid_bytes)

    def readBool(self):
        return bool(self.readUint32())

    def readRWChunkHeader(self):
        return {
            "id": self.readUint32(),
            "size": self.readUint32(),
            "version": self.readUint32(),
        }

    def peekRWChunkHeader(self):
        return {
            "id": self.peekUint32(),
            "size": self.peekUint32(),
            "version": self.peekUint32(),
        }

    def readColor32(self) -> dict[str, int]:
        r = self.readUint8()
        g = self.readUint8()
        b = self.readUint8()
        a = self.readUint8()
        return {"r": r, "g": g, "b": b, "a": a}
