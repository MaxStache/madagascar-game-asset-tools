import io
import uuid
import wave as wavefile
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import override

from madagascar.lib import ima_adpcm
from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from madagascar.sections.RWA.WAVESTRUCT_0803 import (
    FLAG_HAS_AUX,
    FLAG_HAS_CODEC,
    FLAG_HAS_IDENTIFIER,
    FLAG_HAS_NAME,
    CodecUUID,
    RWA_WaveFormat,
    RWA_WaveStruct,
)
from madagascar.sections.RWA.WAVEDATA_0804 import RWA_WaveData

# ---------------------------------------------------------------------------
# Template values for waves built from scratch (`RWA_Wave.from_wav`).
#
# Taken from the retail Xbox dictionaries: every one of the 1,391 shipped waves
# across all 16 `*_WavDictXBOX.rws` files carries exactly these values, so a
# generated wave is indistinguishable from a shipped one apart from its name,
# identifier GUID and sample data.
# ---------------------------------------------------------------------------

_RETAIL_FLAGS = FLAG_HAS_IDENTIFIER | FLAG_HAS_NAME | FLAG_HAS_CODEC | FLAG_HAS_AUX  # 0xF

# Runtime pointer on disk; the loader only tests it for != 0, and a nonzero value
# is what makes the codec GUID get written at all. Retail value kept verbatim.
_RETAIL_FORMAT_REF = 4568152

_RETAIL_SOURCE_TAIL = b"\x00\x00\x43\x00"
_RETAIL_DEST_TAIL = b"\x00\x00\x00\x00"
_RETAIL_DEST_PAD0 = 70

# Class GUIDs for the decoder and auxiliary objects; constant across the corpus.
_RETAIL_DECODER_UUID = uuid.UUID("ca5e5be6-b366-4739-8fa5-f3c8bbd5e529")
_RETAIL_AUX_UUID = uuid.UUID("55ad338c-145e-457e-a75b-1f55dd97b7ef")

# Xbox IMA ADPCM packs each channel into a 0x24-byte slice of the block.
_XBOX_IMA_CHANNEL_BLOCK = 0x24


def _byteswap16(data: bytes) -> bytes:
    """Swap the byte order of 16-bit samples (big-endian <-> little-endian)."""
    even = len(data) - (len(data) % 2)
    samples = array("h")
    samples.frombytes(data[:even])
    samples.byteswap()
    return samples.tobytes() + data[even:]


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

    # ------------------------------------------------------------------
    # WAV import / export
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """The wave's stream name."""
        return self.wave_struct.stream_name

    @property
    def duration(self) -> float:
        """Length in seconds, or 0.0 if the format fields are unusable."""
        fmt = self.wave_struct.dest_format
        bytes_per_frame = fmt.channels * max(1, fmt.bit_depth // 8)
        if not fmt.sample_rate or not bytes_per_frame:
            return 0.0
        return len(self.wave_data.data) / bytes_per_frame / fmt.sample_rate

    def to_pcm16(self, big_endian: bool = False) -> bytes:
        """Decode this wave's sample data to interleaved little-endian PCM16.

        Args:
            big_endian: The sample data is stored big-endian (GCN/Wii). The
                dictionary knows this -- see `RW_WaveDict_Dict.is_big_endian`.

        Raises:
            NotImplementedError: The wave uses a codec with no decoder here.
        """
        codec = self.wave_struct.codec
        data = self.wave_data.data

        if codec is CodecUUID.PCM16:
            return _byteswap16(data) if big_endian else data

        if codec is CodecUUID.XBOXIMA:
            channels = max(1, self.wave_struct.source_format.channels)
            return ima_adpcm.decode(
                data, channels, _XBOX_IMA_CHANNEL_BLOCK * channels
            )

        label = codec.name if codec else str(self.wave_struct.codec_uuid)
        raise NotImplementedError(
            f"No decoder for codec {label}; cannot export {self.name!r} to WAV."
        )

    def export_wav(
        self, filepath: str | Path, big_endian: bool = False
    ) -> None:
        """Write this wave out as a .wav file.

        Compressed waves are decoded to PCM16 first, so the exported file is
        always 16-bit PCM regardless of how the wave is stored.

        Args:
            filepath: Destination .wav path.
            big_endian: The sample data is stored big-endian (GCN/Wii).
        """
        pcm = self.to_pcm16(big_endian=big_endian)
        fmt = self.wave_struct.dest_format

        with wavefile.open(str(filepath), "wb") as out:
            out.setnchannels(max(1, fmt.channels))
            out.setsampwidth(2)  # to_pcm16 always yields 16-bit samples
            out.setframerate(fmt.sample_rate)
            out.writeframes(pcm)

    def import_wav(
        self, filepath: str | Path, big_endian: bool = False
    ) -> None:
        """Replace this wave's sample data with the contents of a .wav file.

        The wave's name and identifier GUID are left alone, so the dictionary
        entry keeps its identity and only the audio changes. Sample rate,
        channel count and sizes are taken from the .wav. The result is stored
        as PCM16 -- there is no encoder for the compressed codecs here, so a
        wave that was compressed becomes uncompressed.

        Args:
            filepath: Source .wav file. Must be 16-bit PCM.
            big_endian: Store the sample data big-endian (GCN/Wii).

        Raises:
            ValueError: The .wav is not 16-bit PCM.
        """
        pcm, sample_rate, channels = _read_wav_pcm16(filepath)

        if big_endian:
            pcm = _byteswap16(pcm)

        self.wave_data.data = pcm

        for fmt in (self.wave_struct.source_format, self.wave_struct.dest_format):
            fmt.sample_rate = sample_rate
            fmt.channels = channels
            fmt.bit_depth = 16
            fmt.codec_uuid = CodecUUID.PCM16.value
            if fmt._format_ref == 0:
                fmt._format_ref = _RETAIL_FORMAT_REF

        # Keeps the declared sizes in step with the new buffer.
        self.sync_sizes()

    @classmethod
    def from_wav(
        cls,
        filepath: str | Path,
        name: str | None = None,
        big_endian: bool = False,
        loop: bool = False,
    ) -> "RWA_Wave":
        """Build a brand-new wave from a .wav file, ready to append to a dict.

        Every field other than the name, identifier and samples is filled from
        the retail template (see the module constants), so the result matches
        what the shipped dictionaries contain.

        Args:
            filepath: Source .wav file. Must be 16-bit PCM.
            name: Stream name. Defaults to the .wav filename without extension.
            big_endian: Store the sample data big-endian (GCN/Wii).
            loop: Value for the wave's loop flag.

        Returns:
            A new RWA_Wave. Append it to `dict.wave.streams`; the subsong count
            is re-derived on write.
        """
        pcm, sample_rate, channels = _read_wav_pcm16(filepath)

        if big_endian:
            pcm = _byteswap16(pcm)

        def _make_format(tail: bytes, pad0: int) -> RWA_WaveFormat:
            return RWA_WaveFormat(
                sample_rate=sample_rate,
                _format_ref=_RETAIL_FORMAT_REF,
                data_size=len(pcm),
                bit_depth=16,
                channels=channels,
                _pad0=pad0,
                _tail=tail,
                codec_uuid=CodecUUID.PCM16.value,
            )

        new_wave = cls()
        new_wave.wave_struct = RWA_WaveStruct(
            flags=_RETAIL_FLAGS,
            source_format=_make_format(_RETAIL_SOURCE_TAIL, 0),
            dest_format=_make_format(_RETAIL_DEST_TAIL, _RETAIL_DEST_PAD0),
            loop_stream_flag=1 if loop else 0,
            # Waves are identified by a unique GUID; a fresh one avoids
            # colliding with any entry already in the dictionary.
            identifier_uuid=uuid.uuid4(),
            stream_name=name if name is not None else Path(filepath).stem,
            decoder_uuid=_RETAIL_DECODER_UUID,
            aux_uuid=_RETAIL_AUX_UUID,
        )
        new_wave.wave_data = RWA_WaveData(data=pcm)

        return new_wave

    @override
    def __repr__(self):
        return f"RWA_Wave({self.wave_struct!r}, {self.wave_data!r})"


def _read_wav_pcm16(filepath: str | Path) -> tuple[bytes, int, int]:
    """Read a 16-bit PCM .wav, returning (frames, sample_rate, channels)."""
    with wavefile.open(str(filepath), "rb") as src:
        width = src.getsampwidth()
        if width != 2:
            raise ValueError(
                f"{filepath}: expected 16-bit PCM, got {width * 8}-bit. "
                "Convert the file first; there is no encoder here."
            )
        channels = src.getnchannels()
        sample_rate = src.getframerate()
        frames = src.readframes(src.getnframes())

    return frames, sample_rate, channels
