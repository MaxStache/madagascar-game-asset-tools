from dataclasses import dataclass, field
from typing import override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RWA_WaveData(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    
    data: bytes = b""  # Wave data bytes


    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RWA_WaveData":
        wave_dta = cls()
        wave_dta.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            wave_dta.header,
            RWSectionType.rwaID_WAVEDATA.value,
            "RWA_Wave chunk type",
        )
        
        wave_dta.data = parser.readBytes(wave_dta.header.size)  # Read the wave data bytes

        return wave_dta

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        # The chunk body is the sample data verbatim -- no struct, no padding.
        rw_header = RWHeader(
            type=RWSectionType.rwaID_WAVEDATA.value,
            size=len(self.data),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(self.data)

    @override
    def __repr__(self):
        return f"RWA_WaveData({len(self.data)} bytes)"