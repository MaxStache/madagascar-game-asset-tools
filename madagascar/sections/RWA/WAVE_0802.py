import io
from dataclasses import dataclass, field
from typing import override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from madagascar.sections.RWA.WAVESTRUCT_0803 import RWA_WaveStruct
from madagascar.sections.RWA.WAVEDATA_0804 import RWA_WaveData


@dataclass
class RWA_Wave(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    wave_struct: RWA_WaveStruct = field(default_factory=RWA_WaveStruct)
    wave_data: RWA_WaveData = field(default_factory=RWA_WaveData)

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RWA_Wave":
        wave = cls()
        wave.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            wave.header,
            RWSectionType.rwaID_WAVE.value,
            "RWA_Wave chunk type",
        )

        wave.wave_struct = RWA_WaveStruct.read(parser, parent=wave)
        wave.wave_data = RWA_WaveData.read(parser, parent=wave)

        return wave

    def sync_sizes(self) -> None:
        """Make the wave struct's declared sizes agree with the actual sample data.

        `source_format.data_size` is what the loader uses to size its read of the
        0x804 body, so a replaced sample buffer that leaves it stale produces a
        file the game reads past the end of (or truncates). `dest_format` holds
        the *decoded* size, which only equals the stored size when the data is
        uncompressed -- so it is updated only when it already tracked the source,
        leaving genuinely compressed waves alone.
        """
        actual = len(self.wave_data.data)
        tracked = self.wave_struct.dest_format.data_size == self.wave_struct.source_format.data_size

        self.wave_struct.source_format.data_size = actual
        if tracked:
            self.wave_struct.dest_format.data_size = actual

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        self.sync_sizes()

        buf = io.BytesIO()

        self.wave_struct.write(buf, stamp, parent=self)
        self.wave_data.write(buf, stamp, parent=self)

        payload = buf.getvalue()
        rw_header = RWHeader(
            type=RWSectionType.rwaID_WAVE.value,
            size=len(payload),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(payload)

    @override
    def __repr__(self):
        return f"RWA_Wave({self.wave_struct!r}, {self.wave_data!r})"
