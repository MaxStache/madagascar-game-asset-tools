import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union
from lib.parser import Parser
from rwConstants import (
    RWSectionType,
    strfunc_func,
    MAKECHUNKID,
    rwVENDORID_CRITERIONRM,
)
import uuid
from lib.entityAttributeDocs import CREATE_ENTITY_ATTRIBUTE_COMMANDS

__version__ = "1.0.0"

# ═══════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════

DEFAULT_VERSION_STAMP = 0x1C020016

# ═══════════════════════════════════════════════════════
#  Data Structures
# ═══════════════════════════════════════════════════════


@dataclass
class RWHeader:
    type: int = 0
    size: int = 0
    library_id_stamp: int = DEFAULT_VERSION_STAMP

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

    def getIsComplex(self) -> bool:
        t = self.type

        if t in (
            RWSectionType.rwID_STRUCT.value,
            RWSectionType.rwID_STRING.value,
            RWSectionType.rwID_EXTENSION.value,
            RWSectionType.rwID_MATRIX.value,
            RWSectionType.rwID_UNICODESTRING.value,
        ):
            return False

        if t in (
            RWSectionType.rwID_CAMERA.value,
            RWSectionType.rwID_TEXTURE.value,
            RWSectionType.rwID_MATERIAL.value,
            RWSectionType.rwID_MATLIST.value,
            RWSectionType.rwID_ATOMICSECT.value,
            RWSectionType.rwID_PLANESECT.value,
            RWSectionType.rwID_WORLD.value,
            RWSectionType.rwID_FRAMELIST.value,
            RWSectionType.rwID_GEOMETRY.value,
            RWSectionType.rwID_CLUMP.value,
            RWSectionType.rwID_LIGHT.value,
            RWSectionType.rwID_ATOMIC.value,
            RWSectionType.rwID_GEOMETRYLIST.value,
        ):
            return True

        return False

    @property
    def version(self) -> str:
        if self.library_id_stamp & 0xFFFF0000:
            v = (self.library_id_stamp >> 14 & 0x3FF00) + 0x30000
            v |= self.library_id_stamp >> 16 & 0x3F
            return f"{(v >> 16) & 0xF}.{(v >> 12) & 0xF}.{(v >> 8) & 0xF}.{v & 0xFF}"
        return "3.1.0.0"


@dataclass
class RW_strfunc_CreateEntity:
    pass


@dataclass
class RW_strfunc_PlacementNew:
    pass


@dataclass
class RW_strfunc_SetFrozenMode:
    @property
    def strfunc(self):
        return strfunc_func.sf_SetFrozenMode

    def get_raw_data(self):
        return b""


@dataclass
class RW_strfunc_LoadEmbeddedAsset:
    pass


@dataclass
class RW_StreamFileSector:
    header: RWHeader = field(default_factory=RWHeader)
    data: bytes = field(default_factory=bytes)

    def read(self, parser: Parser):
        self.header = RWHeader.read(parser)
        self.data = parser.readBytes(self.header.size)


def _SectorClass_to_RW_StreamFileSector(sector) -> RW_StreamFileSector:
    if not hasattr(sector, "strfunc"):
        raise ValueError("Object does not have a strfunc property")
    if not hasattr(sector, "get_raw_data"):
        raise ValueError("Object does not have a get_raw_data method")

    chunk_type = MAKECHUNKID(rwVENDORID_CRITERIONRM, sector.strfunc.value)
    chunk_data = sector.get_raw_data()

    new_sector = RW_StreamFileSector(
        header=RWHeader(
            type=chunk_type,
            size=len(chunk_data),
            library_id_stamp=DEFAULT_VERSION_STAMP,
        ),
        data=chunk_data,
    )

    return new_sector


@dataclass
class RW_StreamFile:
    contents: list[RW_StreamFileSector] = field(default_factory=list)

    def save(self, filepath: Union[str, Path]):
        buf = io.BytesIO()

        for sector in self.contents:
            _write_header(
                buf,
                sector.header.type,
                len(sector.data),
                sector.header.library_id_stamp,
            )
            _write_bytes(buf, sector.data)

        with open(filepath, "wb") as f:
            f.write(buf.getvalue())

    def append(self, sectorClass):
        result = _SectorClass_to_RW_StreamFileSector(sectorClass)
        self.contents.append(result)

    def replace_at_index(self, index: int, sectorClass):
        if index < 0 or index >= len(self.contents):
            raise IndexError("Index out of range")
        result = _SectorClass_to_RW_StreamFileSector(sectorClass)
        self.contents[index] = result


# ═══════════════════════════════════════════════════════
#  helpers
# ═══════════════════════════════════════════════════════


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


def expect_chunk_type_or_raise(
    header: RWHeader, expected_type: int, error: str = "Wrong Chunk Type"
):
    if header.type != expected_type:
        raise ValueError(
            f"{error}: expected 0x{expected_type:02X}, got 0x{header.type:02X} ({int(header.type)})"
        )


def load_stream(filepath: Union[str, Path]) -> RW_StreamFile:
    """Load a STREAM level file from disk

    Args:
        filepath: Path to the .stream file.

    Returns:
        Parsed Stream File.
    """
    stream = RW_StreamFile()

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

        while True:
            if not parser.canRead(RWHeader().binSize):
                break

            sector = RW_StreamFileSector()

            sector.read(parser)

            stream.contents.append(sector)

    return stream


def _getStrfuncFromChunkType(chunk_type: int) -> str:
    for func in strfunc_func:
        if MAKECHUNKID(rwVENDORID_CRITERIONRM, func.value) == chunk_type:
            return func
    return None


def _ParseMatrix4x4(data):
    buf = Parser(data, endian="little")

    matrix = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]

    matrix[0][0] = buf.readFloat()
    matrix[0][1] = buf.readFloat()
    matrix[0][2] = buf.readFloat()
    matrix[0][3] = buf.readFloat()

    matrix[1][0] = buf.readFloat()
    matrix[1][1] = buf.readFloat()
    matrix[1][2] = buf.readFloat()
    matrix[1][3] = buf.readFloat()

    matrix[2][0] = buf.readFloat()
    matrix[2][1] = buf.readFloat()
    matrix[2][2] = buf.readFloat()
    matrix[2][3] = buf.readFloat()

    matrix[3][0] = buf.readFloat()
    matrix[3][1] = buf.readFloat()
    matrix[3][2] = buf.readFloat()
    matrix[3][3] = buf.readFloat()

    return matrix



def _write_log_HandleAttribute(f, command, data, strCurrentClass, offset=0x0):
    attrDocumentation = CREATE_ENTITY_ATTRIBUTE_COMMANDS.get(strCurrentClass, {}).get(
        int(command), None
    )

    if strCurrentClass == "CTFBModel" and command == 1:
        val = Parser(data, endian="little")

        with open("CTFBModel_Cmd1.txt", "a") as ctfblog:
            ctfblog.write(data.hex() + "\n")

    if attrDocumentation:
        output = f"\t\t{hex(offset)} - {attrDocumentation['name']:<15}"
    else:
        output = f"\t\t{hex(offset)} - Attribute {command:>3}"

    if attrDocumentation and data:
        if attrDocumentation["data"]["type"] == "GUID":
            guid = uuid.UUID(bytes=data[:16])
            output += f": {{{guid}}}"
        if attrDocumentation["data"]["type"] == "BOOLEAN":
            value = int.from_bytes(data[:1], byteorder="little")
            output += f": RWBool({value}) ({bool(value)})"
        if attrDocumentation["data"]["type"] == "MESSAGE":
            buf = Parser(data, endian="little")
            value = buf.readPaddedCString().strip()
            displayValue = value if value else "<No Message>"
            output += f": {displayValue:<20} {'(message)' if value else ''}"
        if attrDocumentation["data"]["type"] == "RwUInt32":
            buf = Parser(data, endian="little")
            value = buf.readUint32()
            if attrDocumentation["data"].get("list"):
                value = (
                    f"{attrDocumentation['data']['list']['values'][value]} ({value})"
                )
            output += f": {value}"
        if attrDocumentation["data"]["type"] == "RwV3d":
            buf = Parser(data, endian="little")
            x = buf.readFloat()
            y = buf.readFloat()
            z = buf.readFloat()
            output += f": ({x}, {y}, {z})"
        if attrDocumentation["data"]["type"] == "RwReal":
            buf = Parser(data, endian="little")
            value = buf.readFloat()
            output += f": {value}"
        if attrDocumentation["data"]["type"] == "RwChar":
            buf = Parser(data, endian="little")
            if attrDocumentation["data"].get("read") == "CString":
                value = buf.readCString().strip()
            else:
                value = buf.readCString().strip()
            output += f": {value}"
        if attrDocumentation["data"]["type"] == "RwRGBA":
            buf = Parser(data, endian="little")
            value = buf.readColor32()
            output += f": RGBA({value['r']}, {value['g']}, {value['b']}, {value['a']})"
        if attrDocumentation["data"]["type"] == "Matrix4x4":
            prefixLen = len(output.replace("\t", "    ") + ": Matrix4x4(")

            value = _ParseMatrix4x4(data)

            # Format values first
            formatted = [[f"{v:.3f}" for v in row] for row in value]

            # Column widths
            col_widths = [max(len(row[col]) for row in formatted) for col in range(4)]

            # Build aligned rows
            rows = []
            for row in formatted:
                padded = [row[i].ljust(col_widths[i]) for i in range(4)]
                rows.append("[" + ", ".join(padded) + "]")

            output += f": Matrix4x4({rows[0]}\n"

            for row in rows[1:-1]:
                output += f"{' ' * prefixLen}{row}\n"

            output += f"{' ' * prefixLen}{rows[-1]})"
    else:
        textChars = data

        # Text view: alpha chars kept, others replaced with space, padded to 15
        textView = ""
        for b in textChars:
            if (
                (48 <= b <= 57)
                or (65 <= b <= 90)
                or (97 <= b <= 122)
                or b
                in (
                    95,
                    45,
                    33,
                    63,
                    46,
                    92,
                    47,
                    58,
                    40,
                    41,
                    61,
                    123,
                    125,
                    91,
                    93,
                    38,
                    36,
                    43,
                    42,
                    35,
                )
            ):
                textView += chr(b)
            else:
                textView += " "

        # Hex view: uppercase, 2-digit, space separated
        hexParts = [f"{b:02X}" for b in textChars]
        hexView = " ".join(hexParts)

        output += f": [{textView}][{hexView}]"

    f.write(output + "\n")


def _write_log_HandleAttributes(f, data):
    RWSPH_CLASSID = 0x80000000  # Class
    RWSPH_INSTANCEID = 0x40000000  # Entity ID
    RWSPH_CREATECLASSID = 0x20000000  # Behavior

    strCurrentClass = ""

    buf = Parser(data, endian="little")

    while buf.canRead(4):
        packetStart = buf.tell()
        packetSize = buf.readUint32()
        if packetSize == 0:
            break

        command = buf.readUint32()
        dataSize = packetSize - 2 * 4  # subtract the two uint32s (size + command)

        if command == RWSPH_CLASSID:
            dataBytes = buf.readBytes(dataSize)
            strCurrentClass = dataBytes.split(b"\x00")[0].decode(
                "ascii", errors="replace"
            )
            f.write(f"\tClass:\t{strCurrentClass}\n")

        elif command == RWSPH_INSTANCEID:
            entityID = uuid.UUID(bytes=buf.readBytes(16))
            f.write(f"\tEntity ID:\t{{{entityID}}}\n")

        elif command == RWSPH_CREATECLASSID:
            dataBytes = buf.readBytes(dataSize)

            behaviour = dataBytes.split(b"\x00")[0].decode("ascii", errors="replace")
            f.write(f"\tBehaviour:\t{behaviour}\n")
        else:
            # if command == 0 and strCurrentClass == "CSystemCommands":
            #    assetID = uuid.UUID(bytes=buf.readBytes(16))
            #    f.write(f"\t\tAttach asset, ID:\t{{{assetID}}}\n")
            # else:
            _write_log_HandleAttribute(
                f, command, buf.readBytes(dataSize), strCurrentClass, offset=buf.tell()
            )

        # Advance to next packet (ensures correct alignment regardless of how much data was consumed)
        buf.seek(packetStart + packetSize)


def _write_log_strfunc_CreateEntity(f, idx, e: RW_StreamFileSector):
    f.write("Create Entity Call:\n")

    buf = Parser(e.data, endian="little")
    isGlobal = buf.readBool()

    attributePacket = buf.readBytes(len(e.data) - 4)

    _write_log_HandleAttributes(f, attributePacket)

    f.write(f"\tisGlobal:\t{isGlobal}\n")
    f.write("\n")


def _write_log_strFunc_PlacementNew(f, idx, e: RW_StreamFileSector):
    f.write("Data:\n")

    # read entire chunk into a sub-buffer, advancing the stream past it
    buf = Parser(e.data, endian="little")

    elementCount = buf.readUint32()

    for element in range(0, elementCount):
        behaviour = buf.readPaddedCString()
        entityCount = buf.readUint32()
        f.write(f"    {behaviour} Count:{entityCount}\n")

    f.write("\n")


def _write_log_strfunc_LoadEmbeddedAsset(f, idx, e: RW_StreamFileSector):
    f.write("Asset Header:\n")

    parser = Parser(e.data, endian="little")

    headerSize = parser.readUint32()

    # read entire chunk into a sub-buffer
    buf = Parser(parser.readBytes(headerSize), endian="little")

    dataSize = parser.readUint32()

    nameLength = buf.readUint32()
    name = buf.readPaddedCString(nameLength)

    guid = buf.readGUID()

    typeLength = buf.readUint32()
    assetType = buf.readPaddedCString(typeLength)

    fileLength = buf.readUint32()
    file = buf.readPaddedCString(fileLength)

    depsSize = buf.readUint32()
    dependecies = buf.readPaddedCString(depsSize)

    f.write(f"\t- Header Size: {headerSize}\n")
    f.write(f"\t- Data Size: {dataSize}\n")

    f.write(f"\t- Name Length: {nameLength}\n")
    f.write(f"\t  Asset Name: {name}\n")

    f.write(f"\t- Asset GUID: {str(guid)}\n")

    f.write(f"\t- Type Length: {typeLength}\n")
    f.write(f"\t  Asset Type: {assetType}\n")

    f.write(f"\t- File Length: {fileLength}\n")
    f.write(f"\t  Asset File: {file}\n")

    f.write(f"\t- Dependecies Length: {depsSize}\n")
    f.write(f"\t  Asset Dependecies: {dependecies}\n")

    f.write("\n")


def _strfunc_to_chunktype(strfunc: strfunc_func) -> int:
    return MAKECHUNKID(rwVENDORID_CRITERIONRM, strfunc.value)


def write_log(stream: RW_StreamFile, output_path: Union[str, Path]):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("Read a file stream\n\n")
        for idx, e in enumerate(stream.contents):
            f.write(f"{'═' * 20} Sector {idx} {'═' * 20}\n")
            f.write(
                f"Length: {e.header.size} Type: {e.header.type} ({_getStrfuncFromChunkType(e.header.type).name})\n"
            )

            # CreateEntity
            if e.header.type == _strfunc_to_chunktype(strfunc_func.sf_CreateEntity):
                _write_log_strfunc_CreateEntity(f, idx, e)

            # PlacementNew
            elif e.header.type == _strfunc_to_chunktype(strfunc_func.sf_PlacementNew):
                _write_log_strFunc_PlacementNew(f, idx, e)

            # LoadEmbeddedAsset
            elif e.header.type == _strfunc_to_chunktype(
                strfunc_func.sf_LoadEmbeddedAsset
            ):
                _write_log_strfunc_LoadEmbeddedAsset(f, idx, e)

            # Unhandled
            else:
                f.write("\t[No view defined]\n\n")
