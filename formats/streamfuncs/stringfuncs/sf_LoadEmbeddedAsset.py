import io
from dataclasses import dataclass, field
import uuid

from formats.lib.parser import Parser
from formats.lib.writer import _write_alignedString, _write_u32
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise

@dataclass
class RW_sf_LoadEmbeddedAsset(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)
    
    headerSize: int = 0
    dataSize: int = 0

    nameLength: int = 0
    name: str = ""

    guid: uuid.UUID = field(default=None)

    typeLength: int = 0
    type: str = ""

    filePathLength: int = 0
    filePath: str = ""

    depsSize: int = 0
    deps: str = ""

    data: bytes = b""

    @staticmethod
    def read(parser: Parser) -> "RW_sf_LoadEmbeddedAsset":
        sf_LEA = RW_sf_LoadEmbeddedAsset()
        sf_LEA.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            sf_LEA.header,
            strfunc_func.sf_LoadEmbeddedAsset.value,
            "RW_sf_LoadEmbeddedAsset chunk type",
        )

        buf = Parser(parser.readBytes(sf_LEA.header.size), endian="little")

        sf_LEA.headerSize = buf.readUint32()

        # -- header
        headerParser = Parser(buf.readBytes(sf_LEA.headerSize), endian="little")
        sf_LEA.nameLength = headerParser.readUint32()
        sf_LEA.name = headerParser.readPaddedCString(sf_LEA.nameLength)

        sf_LEA.guid = headerParser.readGUID()

        sf_LEA.typeLength = headerParser.readUint32()
        sf_LEA.type = headerParser.readPaddedCString(sf_LEA.typeLength)

        sf_LEA.filePathLength = headerParser.readUint32()
        sf_LEA.filePath = headerParser.readPaddedCString(sf_LEA.filePathLength)

        sf_LEA.depsSize = headerParser.readUint32()
        sf_LEA.deps = headerParser.readPaddedCString(sf_LEA.depsSize)
        # ---

        sf_LEA.dataSize = buf.readUint32()
        sf_LEA.data = buf.readBytes(sf_LEA.dataSize)

        return sf_LEA

    def write(this, f, stamp):
        buf = io.BytesIO()

        rw_header = RWHeader(
            type=strfunc_func.sf_LoadEmbeddedAsset.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())