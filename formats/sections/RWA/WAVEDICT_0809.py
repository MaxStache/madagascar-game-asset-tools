import io
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise
from formats.sections.RWA.WAVEDICT_DICT_080A import RW_WaveDict_Dict
from formats.sections.RWA.WAVEDICT_WAVE_080C import RW_WaveDict_Wave

@dataclass
class RW_WaveDict(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    dict: RW_WaveDict_Dict = field(default_factory=RW_WaveDict_Dict)
    wave: RW_WaveDict_Wave = field(default_factory=RW_WaveDict_Wave)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_WaveDict":
        wavedict = RW_WaveDict()
        wavedict.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            wavedict.header,
            RWSectionType.rwaID_WAVEDICT.value,
            "RW_WaveDict chunk type",
        )

        wavedict.dict = RW_WaveDict_Dict.read(parser, parent=wavedict)
        wavedict.wave = RW_WaveDict_Wave.read(parser, parent=wavedict)

        return wavedict

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=RWSectionType.rwaID_WAVEDICT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())