import io
from dataclasses import dataclass, field
from typing import Any, BinaryIO, override

from formats.lib.parser import Parser
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_StreamFunc, RWHeader, expect_chunk_type_or_raise



@dataclass
class RW_sf_StartSystem(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    @classmethod
    @override
    def read(cls, parser: Parser) -> "RW_sf_StartSystem":
        sf = cls()

        sf.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            sf.header,
            strfunc_func.sf_StartSystem.value,
            "RW_sf_StartSystem chunk type",
        )

        return sf

    @override
    def write(self, f: BinaryIO, stamp: int):
        buf = io.BytesIO()


        rw_header = RWHeader(
            type=strfunc_func.sf_StartSystem.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    @property
    @override
    def streamfunc(self):
        return strfunc_func.sf_StartSystem

    @override
    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
        }

    @classmethod
    @override
    def from_dict(cls, content: dict[str, Any]) -> "RW_StreamFunc":
        header = RWHeader.from_dict(content.get("header", {}))

        return cls(header=header)