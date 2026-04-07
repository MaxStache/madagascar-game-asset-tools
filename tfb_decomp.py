import struct
import uuid


class Parser:
    def __init__(self, data: bytes, endian: str = "little"):
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes or bytearray")

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

    def _read(self, fmt: str):
        size = struct.calcsize(fmt)
        if self.offset + size > len(self.data):
            raise EOFError("Attempt to read past end of buffer")

        value = struct.unpack_from(fmt, self.data, self.offset)
        self.offset += size
        return value[0] if len(value) == 1 else value

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

    def skip(self, size: int):
        self.seek(self.offset + size)

    def canRead(self, size: int) -> bool:
        return self.offset + size <= len(self.data)

    # -------------------------
    # Integer reads
    # -------------------------

    def readUint8(self):
        return self._read(self.endian + "B")

    def readInt8(self):
        return self._read(self.endian + "b")

    def readUint16(self):
        return self._read(self.endian + "H")

    def readInt16(self):
        return self._read(self.endian + "h")

    def readUint32(self):
        return self._read(self.endian + "I")

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

    def readCString(self, encoding="utf-8") -> str:
        start = self.offset
        while self.offset < len(self.data) and self.data[self.offset] != 0:
            self.offset += 1

        if self.offset >= len(self.data):
            raise EOFError("Unterminated C string")

        s = self.data[start : self.offset].decode(encoding)
        self.offset += 1  # skip null byte
        return s

    def readPaddedCString(self, alignment=4, encoding="utf-8") -> str:
        start = self.offset
        s = self.readCString(encoding)
        byte_length = self.offset - start  # actual bytes consumed including null
        remainder = byte_length % alignment
        if remainder:
            self.offset += alignment - remainder
        return s
    
    def readStringPrefixedLength(self, encoding="utf-8") -> str:
        length = self.readUint8()
        s = self.readBytes(length).decode(encoding)
        return s

    def readGUID(self):
        guid_bytes = self.readBytes(16)
        return uuid.UUID(bytes=guid_bytes)

    def readBool(self):
        return self.readUint32() != 0
    
def readStringTable(buf):
    stringCount = buf.readUint32()
    strings = []
    for _ in range(stringCount):
        s = buf.readStringPrefixedLength()
        meta = buf.readUint32()
        strings.append(s)
    return strings
    
def readInstruction(buf: Parser):
    opcode = buf.readUint8()
    
    a = buf.readUint8()
    b = buf.readUint8()
    c = buf.readUint8()
    d = buf.readUint8()
    
    payloadSize = buf.readUint8()
    payload = buf.readBytes(payloadSize)
    
    return {
        "opcode": opcode,
        "a": a,
        "b": b,
        "c": c,
        "d": d,
        "payload": payload
    }

def readTFBScript(data):
    buf = Parser(data, endian="little")
    scriptName = buf.readStringPrefixedLength()
    functionCount = buf.readUint32()
    stringTable1 = readStringTable(buf)
    stringTable2 = readStringTable(buf)
    stringTable3 = readStringTable(buf)
    
    instructionCount = buf.readUint32()
    instructions = []
    for _ in range(instructionCount):
        instructions.append(
            readInstruction(buf)
        )
        
    print(stringTable1)
    print(stringTable2)
    print(stringTable3)
    
    for inst in instructions:
        if inst["opcode"] != 255:
            stringOpcode = stringTable1[inst["opcode"]]
            if (stringOpcode == "comment:::op-code"):
                print("COMMENT:", inst["payload"].decode("utf-8", errors="ignore").strip())
            else:
                print(stringTable1[inst["opcode"]], inst["a"], inst["b"], inst["c"], inst["d"], inst["payload"].hex())
        else:
            print("OPCODE_255", inst["a"], inst["b"], inst["c"], inst["d"], inst["payload"].hex())

ME_Hint = "ENG_KoNY_LPA/702_ME_Hint.ai"
ME_Zoo_Gates = "ENG_KoNY_LPA/704_ME_Zoo_Gates.ai"
RW_Balloon = "ENG_KoNY_LPA/556_RW_Balloon.ai"

with open(RW_Balloon, "rb") as f:
    f.seek(0)
    data = f.read()
    readTFBScript(data)
    
hexData = "00 C0 FF FF 00 00 02 00"
data = bytes.fromhex(''.join(hexData.split()))
buf = Parser(data, endian="little")