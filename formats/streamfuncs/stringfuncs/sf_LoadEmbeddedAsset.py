import io
from dataclasses import dataclass, field
import uuid

from formats.lib.parser import Parser
from formats.lib.writer import (
    _write_alignedString,
    _write_guid,
    _write_lengthPrefixedString,
    _write_u32,
)
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise


@dataclass
class RW_sf_LoadEmbeddedAsset(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    headerSize: int = 0
    dataSize: int = 0

    name: str = ""

    guid: uuid.UUID = field(default=None)

    type: str = ""

    filePath: str = ""

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
        sf_LEA.name = headerParser.readLengthPrefixedString(removePadding=True)

        sf_LEA.guid = headerParser.readGUID()

        sf_LEA.type = headerParser.readLengthPrefixedString(removePadding=True)

        sf_LEA.filePath = headerParser.readLengthPrefixedString(removePadding=True)

        sf_LEA.deps = headerParser.readLengthPrefixedString(removePadding=True)
        # ---

        sf_LEA.dataSize = buf.readUint32()
        sf_LEA.data = buf.readBytes(sf_LEA.dataSize)

        return sf_LEA

    def write(this, f, stamp):
        buf = io.BytesIO()

        # --- header
        headerBuf = io.BytesIO()
        _write_lengthPrefixedString(headerBuf, this.name, addNullTerminator=True, alignTo4=True)

        _write_guid(headerBuf, this.guid)

        _write_lengthPrefixedString(headerBuf, this.type, addNullTerminator=True, alignTo4=True)

        _write_lengthPrefixedString(headerBuf, this.filePath, addNullTerminator=True, alignTo4=True)

        _write_lengthPrefixedString(headerBuf, this.deps, addNullTerminator=True, alignTo4=True)

        _write_u32(headerBuf, 0) # doing this because renderware wants it, idk
        # ---

        _write_u32(buf, len(headerBuf.getvalue()))
        buf.write(headerBuf.getvalue())

        _write_u32(buf, len(this.data))
        buf.write(this.data)

        padding_length = (4 - (len(buf.getvalue()) % 4)) % 4
        buf.write(b"\x58" * padding_length)

        rw_header = RWHeader(
            type=strfunc_func.sf_LoadEmbeddedAsset.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    @property
    def streamfunc(self):
        return strfunc_func.sf_LoadEmbeddedAsset
    
    def __repr__(self):
        return f"RW_sf_LoadEmbeddedAsset(name=\"{self.name!r}\", guid=\"{str(self.guid)!r}\", type=\"{self.type!r}\", filePath=\"{self.filePath!r}\", deps=\"{self.deps!r}\", dataSize={len(self.data)!r})"