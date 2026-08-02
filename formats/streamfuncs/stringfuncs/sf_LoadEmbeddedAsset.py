import io
import uuid
from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from formats.lib.parser import Parser
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise
from formats.lib.rwConstants import strfunc_func
from formats.lib.writer import (
    write_guid,
    write_lengthPrefixedString,
    write_u32,
)


@dataclass
class RW_sf_LoadEmbeddedAsset(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    headerSize: int = 0
    dataSize: int = 0

    name: str = ""

    guid: uuid.UUID = field(default=uuid.UUID(int=0))

    type: str = ""

    filePath: str = ""

    deps: str = ""

    data: bytes = b""

    @classmethod
    @override
    def read(cls, parser: Parser) -> "RW_sf_LoadEmbeddedAsset":
        sf_LEA = cls()
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

    @override
    def write(self, f: BinaryIO, stamp: int) -> None:
        buf = io.BytesIO()

        # --- header
        headerBuf = io.BytesIO()
        write_lengthPrefixedString(
            headerBuf, self.name, addNullTerminator=True, alignTo4=True
        )

        write_guid(headerBuf, self.guid)

        write_lengthPrefixedString(
            headerBuf, self.type, addNullTerminator=True, alignTo4=True
        )

        write_lengthPrefixedString(
            headerBuf, self.filePath, addNullTerminator=True, alignTo4=True
        )

        write_lengthPrefixedString(
            headerBuf, self.deps, addNullTerminator=True, alignTo4=True
        )

        write_u32(headerBuf, 0)  # doing this because renderware wants it, idk
        # ---

        write_u32(buf, len(headerBuf.getvalue()))
        buf.write(headerBuf.getvalue())

        write_u32(buf, len(self.data))
        buf.write(self.data)

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
    @override
    def streamfunc(self):
        return strfunc_func.sf_LoadEmbeddedAsset

    @override
    def __repr__(self):
        return f'RW_sf_LoadEmbeddedAsset(name="{self.name!r}", guid="{str(self.guid)!r}", type="{self.type!r}", filePath="{self.filePath!r}", deps="{self.deps!r}", dataSize={len(self.data)!r})'

    @override
    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "name": self.name,
            "guid": str(self.guid),
            "type": self.type,
            "filePath": self.filePath,
            "deps": self.deps,
        }

    @classmethod
    @override
    def from_dict(cls, content: dict[str, Any]) -> "RW_StreamFunc":
        header = RWHeader.from_dict(content.get("header", {}))

        return cls(
            header=header,
            name=content.get("name", ""),
            guid=uuid.UUID(content.get("guid", "00000000-0000-0000-0000-000000000000")),
            type=content.get("type", ""),
            filePath=content.get("filePath", ""),
            deps=content.get("deps", ""),
            data=bytes.fromhex(content.get("data", "")),
        )
