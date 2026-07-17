import io
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_Matrix4x4, RW_StreamFunc, RWHeader, expect_chunk_type_or_raise
from formats.old_stream import _write_f32



@dataclass
class RW_sf_SetDirectorsCameraMatrix(RW_StreamFunc):
    header: RWHeader = field(default_factory=RWHeader)

    matrix: RW_Matrix4x4 = field(default_factory=RW_Matrix4x4)
    fov: float = 0.0

    def read(parser: Parser) -> "RW_sf_SetDirectorsCameraMatrix":
        sf = RW_sf_SetDirectorsCameraMatrix()

        sf.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            sf.header,
            strfunc_func.sf_SetDirectorsCameraMatrix.value,
            "RW_sf_SetDirectorsCameraMatrix chunk type",
        )

        sf.matrix = RW_Matrix4x4.read(parser)
        sf.fov = parser.readFloat()

        return sf

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.matrix.write(buf)
        _write_f32(buf, this.fov)


        rw_header = RWHeader(
            type=strfunc_func.sf_SetDirectorsCameraMatrix.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    @property
    def streamfunc(self):
        return strfunc_func.sf_SetDirectorsCameraMatrix