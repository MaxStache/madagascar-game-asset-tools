import io
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from formats.sections.RWA.WAVE_0802 import RWA_Wave


@dataclass
class RW_WaveDict_Wave(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    total_subsongs: int = 0

    streams: list = field(default_factory=list)
    

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_WaveDict_Wave":
        wave = RW_WaveDict_Wave()
        wave.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            wave.header,
            RWSectionType.rwaID_WAVEDICT_WAVE.value,
            "RW_WaveDict_Wave chunk type",
        )

        wave.total_subsongs = parser.readUint32()

        wave.streams = []
        for i in range( wave.total_subsongs):
            subsong = RWA_Wave.read(parser, parent=wave)
            wave.streams.append(subsong)

        return wave

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=RWSectionType.rwaID_WAVEDICT_WAVE.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())