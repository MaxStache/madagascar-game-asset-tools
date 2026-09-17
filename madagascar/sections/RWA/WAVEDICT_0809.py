import io
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise
from madagascar.sections.RWA.WAVE_0802 import RWA_Wave
from madagascar.sections.RWA.WAVEDICT_DICT_080A import RW_WaveDict_Dict
from madagascar.sections.RWA.WAVEDICT_WAVE_080C import RW_WaveDict_Wave

@dataclass
class RW_WaveDict(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    dict: RW_WaveDict_Dict = field(default_factory=RW_WaveDict_Dict)
    wave: RW_WaveDict_Wave = field(default_factory=RW_WaveDict_Wave)

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_WaveDict":
        wavedict = cls()
        wavedict.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            wavedict.header,
            RWSectionType.rwaID_WAVEDICT.value,
            "RW_WaveDict chunk type",
        )

        wavedict.dict = RW_WaveDict_Dict.read(parser, parent=wavedict)
        wavedict.wave = RW_WaveDict_Wave.read(parser, parent=wavedict)

        return wavedict

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        if isinstance(f, (str, os.PathLike)):
            with open(f, "wb") as out:
                self.write(out, stamp, parent=parent)
            return

        buf = io.BytesIO()

        self.dict.write(buf, stamp, parent=self)
        self.wave.write(buf, stamp, parent=self)

        payload = buf.getvalue()
        rw_header = RWHeader(
            type=RWSectionType.rwaID_WAVEDICT.value,
            size=len(payload),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(payload)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    @property
    def streams(self) -> list[RWA_Wave]:
        """The dictionary's waves (shortcut for `self.wave.streams`)."""
        return self.wave.streams

    @property
    def is_big_endian(self) -> bool:
        """True when this dictionary's sample data is stored big-endian."""
        return self.dict.is_big_endian

    def wave_names(self) -> list[str]:
        """Every wave's stream name, in dictionary order."""
        return [w.wave_struct.stream_name for w in self.wave.streams]

    def find_wave(self, key: int | str) -> RWA_Wave | None:
        """Look a wave up by index or by name, or None if there is no match.

        An `int` is a position in the wave list and may be negative, counting
        from the end. A `str` is matched against the stream name: exactly
        first, then case-insensitively. None of the shipped dictionaries
        contain duplicate names (not even when casefolded), so the first hit is
        unambiguous in practice; if a dictionary does have duplicates, the
        earliest one wins.

        Args:
            key: Wave index, or stream name.

        Returns:
            The matching RWA_Wave, or None.
        """
        streams = self.wave.streams

        if isinstance(key, bool):  # bool is an int subclass; reject it explicitly
            raise TypeError("find_wave() expects an index or a name, not a bool")

        if isinstance(key, int):
            if -len(streams) <= key < len(streams):
                return streams[key]
            return None

        if isinstance(key, str):
            for w in streams:
                if w.wave_struct.stream_name == key:
                    return w

            folded = key.casefold()
            for w in streams:
                if w.wave_struct.stream_name.casefold() == folded:
                    return w
            return None

        raise TypeError(
            f"find_wave() expects an index or a name, got {type(key).__name__}"
        )

    def get_wave(self, key: int | str) -> RWA_Wave:
        """Like `find_wave`, but raises instead of returning None.

        Args:
            key: Wave index, or stream name.

        Raises:
            IndexError: `key` is an out-of-range index.
            KeyError: `key` is a name that is not in the dictionary.
        """
        found = self.find_wave(key)
        if found is not None:
            return found

        if isinstance(key, int):
            raise IndexError(
                f"wave index {key} out of range ({len(self.wave.streams)} waves)"
            )
        raise KeyError(f"no wave named {key!r} in {self.dict.name!r}")

    def add_wave(self, wave: RWA_Wave) -> None:
        """Append a wave and update the subsong count."""
        self.wave.streams.append(wave)
        self.wave.total_subsongs = len(self.wave.streams)

    def __len__(self) -> int:
        return len(self.wave.streams)

    def __iter__(self) -> Iterator[RWA_Wave]:
        return iter(self.wave.streams)

    def __getitem__(self, key: int | str) -> RWA_Wave:
        return self.get_wave(key)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, (int, str)):
            return False
        return self.find_wave(key) is not None

    # ------------------------------------------------------------------
    # WAV import / export
    # ------------------------------------------------------------------

    def export_wav(self, key: int | str, filepath: str | Path) -> None:
        """Export one wave to a .wav file, honouring the dictionary's endianness.

        Args:
            key: Wave index, or stream name.
            filepath: Destination .wav path.
        """
        self.get_wave(key).export_wav(filepath, big_endian=self.is_big_endian)

    def import_wav(self, key: int | str, filepath: str | Path) -> None:
        """Replace one wave's audio from a .wav file, honouring endianness.

        Args:
            key: Wave index, or stream name.
            filepath: Source .wav file. Must be 16-bit PCM.
        """
        self.get_wave(key).import_wav(filepath, big_endian=self.is_big_endian)

    def export_all(
        self,
        output_dir: str | Path,
        raise_on_error: bool = True,
    ) -> list[Path]:
        """Export every wave in the dictionary to .wav files.

        Files are named `<index>_<stream name>.wav`, so waves stay in dictionary
        order and duplicate names cannot collide on disk.

        Args:
            output_dir: Directory to write into (created if needed).
            raise_on_error: Abort on the first wave that cannot be decoded.
                When False, undecodable waves are skipped.

        Returns:
            The paths written.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for i, w in enumerate(self.wave.streams):
            safe = "".join(
                c if c.isalnum() or c in " ._-" else "_" for c in w.wave_struct.stream_name
            ).strip()
            target = out / f"{i}_{safe or 'wave'}.wav"
            try:
                w.export_wav(target, big_endian=self.is_big_endian)
            except NotImplementedError:
                if raise_on_error:
                    raise
                continue
            written.append(target)

        return written

    @override
    def __repr__(self):
        return f"RW_WaveDict({self.dict!r}, {self.wave!r})"