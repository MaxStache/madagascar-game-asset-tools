import io
from dataclasses import dataclass, field
from typing import Any, override

from formats.lib.parser import Parser
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_Matrix4x4, RW_StreamFunc, RWHeader, expect_chunk_type_or_raise
from formats.old_stream import write_f32



@dataclass
class RW_sf_SetDirectorsCameraMatrix(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    matrix: RW_Matrix4x4 = field(default_factory=RW_Matrix4x4)
    fov: float = 0.0

    @classmethod
    @override
    def read(cls, parser: Parser) -> "RW_sf_SetDirectorsCameraMatrix":
        sf = cls()

        sf.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            sf.header,
            strfunc_func.sf_SetDirectorsCameraMatrix.value,
            "RW_sf_SetDirectorsCameraMatrix chunk type",
        )

        sf.matrix = RW_Matrix4x4.read(parser)
        sf.fov = parser.readFloat()

        return sf

    @override
    def write(self, f, stamp):
        buf = io.BytesIO()

        self.matrix.write(buf)
        write_f32(buf, self.fov)


        rw_header = RWHeader(
            type=strfunc_func.sf_SetDirectorsCameraMatrix.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    @property
    @override
    def streamfunc(self):
        return strfunc_func.sf_SetDirectorsCameraMatrix

    @override
    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "matrix": self.matrix.to_dict(),
        }

    @classmethod
    @override
    def from_dict(cls, content: dict[str, Any]) -> "RW_StreamFunc":
        header = RWHeader.from_dict(content.get("header", {}))

        matrix = RW_Matrix4x4.from_dict(content.get("matrix", {}))

        return cls(header=header, matrix=matrix)