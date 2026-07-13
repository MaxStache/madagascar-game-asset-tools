import io
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from formats.sections.RWA.WAVESTRUCT_0803 import RWA_WaveStruct
from formats.sections.RWA.WAVEDATA_0804 import RWA_WaveData


@dataclass
class RWA_Wave(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    wave_struct: RWA_WaveStruct = field(default_factory=RWA_WaveStruct)
    wave_data: RWA_WaveData = field(default_factory=RWA_WaveData)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RWA_Wave":
        wave = RWA_Wave()
        wave.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            wave.header,
            RWSectionType.rwaID_WAVE.value,
            "RWA_Wave chunk type",
        )

        wave.wave_struct = RWA_WaveStruct.read(parser, parent=wave)
        wave.wave_data = RWA_WaveData.read(parser, parent=wave)

        return wave

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=RWSectionType.rwaID_WAVE.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
