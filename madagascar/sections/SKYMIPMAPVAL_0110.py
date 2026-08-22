import io
from dataclasses import dataclass, field
import struct
from typing import override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise


@dataclass
class RW_SkyMipmapVal(RW_Section):
    """See https://gtamods.com/wiki/Sky_Mipmap_Val_(RW_Section)
    """
    header: RWHeader = field(default_factory=RWHeader)

    k_val: int = 0  # signed 12-bit integer
    l_val: int = 0  # unsigned 2-bit integer

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_SkyMipmapVal":
        skymmv = cls()
        skymmv.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            skymmv.header,
            RWSectionType.rwID_SKYMIPMAPVAL.value,
            "RW_SkyMipmapVal chunk type",
        )

        (packed,) = struct.unpack("<I", parser.readBytes(4))

        # Extract signed 12-bit K
        skymmv.k_val = packed & 0xFFF
        if skymmv.k_val & 0x800:
            skymmv.k_val -= 0x1000

        # Extract 2-bit L
        skymmv.l_val = (packed >> 12) & 0x3

        return skymmv

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        # Pack K and L into a single 32-bit integer
        packed = (self.l_val & 0x3) << 12 | (self.k_val & 0xFFF)
        buf.write(struct.pack("<I", packed))

        rw_header = RWHeader(
            type=RWSectionType.rwID_SKYMIPMAPVAL.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
