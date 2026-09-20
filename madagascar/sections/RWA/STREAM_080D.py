import io
import os
import uuid
import wave as wavefile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import override

from madagascar.lib import ima_adpcm
from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise
from madagascar.sections.RWA.STREAM_DATA_080F import RWA_Stream_Data
from madagascar.sections.RWA.STREAM_HDR_080E import (
    RWA_Stream_Header,
    RWA_StreamLayerConfig,
    RWA_StreamLayerInfo,
    RWA_StreamSegmentInfo,
)
from madagascar.sections.RWA.WAVESTRUCT_0803 import CodecUUID

# ---------------------------------------------------------------------------
# rwaID_STREAM (0x80D) -- the game's streamed audio files (*AudioStream*.rws).
#
#   0x80D  stream file
#     0x80E  header   -- segment/layer tables (see STREAM_HDR_080E)
#     0x80F  data     -- every segment's samples in one blob
#
# This is a different format from the wave dictionary (0x809, the level SFX
# banks): there is no per-sound chunk tree, only offsets into one big buffer.
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class RWA_StreamSegment:
    """One sound inside a stream file -- a view, not a chunk of its own.

    Segments are not stored as self-contained records; their name, GUID, offset
    and size live in parallel tables in the 0x80E header. This binds those
    pieces back together so a segment can be handled like a wave.
    """

    stream: "RWA_Stream"
    index: int

    @property
    def info(self) -> RWA_StreamSegmentInfo:
        return self.stream.stream_header.segments[self.index]

    @property
    def name(self) -> str:
        return self.stream.stream_header.segment_names[self.index]

    @property
    def guid(self) -> uuid.UUID:
        return self.stream.stream_header.segment_uuids[self.index]

    def layer_info(self, layer: int = 0) -> RWA_StreamLayerInfo:
        return self.stream.stream_header.layer_infos[layer]

    def layer_config(self, layer: int = 0) -> RWA_StreamLayerConfig:
        return self.stream.stream_header.layer_configs[layer]

    def size(self, layer: int = 0) -> int:
        """Usable (unpadded) byte count of one of this segment's layers."""
        return self.stream.stream_header.usable_size(self.index, layer)

    def duration(self, layer: int = 0) -> float:
        """Length in seconds, or 0.0 when the codec or format is unusable.

        Derived from the stored byte count, so it costs nothing to ask -- no
        decoding happens.
        """
        config = self.layer_config(layer)
        channels = max(1, config.channels)
        stored = len(self.raw(layer))

        if config.codec is CodecUUID.PCM16:
            frames = stored / (channels * max(1, config.bit_depth // 8))
        elif config.codec in (CodecUUID.IMAADPCM, CodecUUID.XBOXIMA):
            frames = ima_adpcm.bytes_to_samples(stored, channels) / channels
        else:
            return 0.0

        return frames / config.sample_rate if config.sample_rate else 0.0

    def raw(self, layer: int = 0) -> bytes:
        """This segment's stored (still encoded) bytes for one layer.

        The streamer reads whole sectors, so a layer is laid out as super-blocks
        of `block_size` usable bytes each padded out to `block_size_padded`.
        Only the usable part of each super-block is audio; this strips the rest.
        """
        info = self.layer_info(layer)
        raw = self.stream.stream_data.data

        pos = self.info.segment_offset + info.layer_start
        remaining = self.size(layer)
        step = info.block_size_padded or info.block_size or remaining

        blocks: list[bytes] = []
        while remaining > 0:
            take = min(info.block_size or remaining, remaining)
            blocks.append(raw[pos : pos + take])
            pos += step
            remaining -= take

        return b"".join(blocks)

    def to_pcm16(self, layer: int = 0) -> bytes:
        """Decode one layer of this segment to interleaved little-endian PCM16.

        Raises:
            NotImplementedError: The layer uses a codec with no decoder here.
        """
        config = self.layer_config(layer)
        info = self.layer_info(layer)
        codec = config.codec
        data = self.raw(layer)

        if codec is CodecUUID.PCM16:
            return data

        if codec in (CodecUUID.IMAADPCM, CodecUUID.XBOXIMA):
            channels = max(1, config.channels)
            # frame_size is the codec's per-channel slice of an interleaved frame.
            pcm = ima_adpcm.decode(data, channels, info.frame_size * channels)
            num_samples = ima_adpcm.bytes_to_samples(len(data), channels)
            return pcm[: num_samples * 2]

        label = codec.name if codec else str(config.codec_uuid)
        raise NotImplementedError(
            f"No decoder for codec {label}; cannot export {self.name!r} to WAV."
        )

    def export_wav(self, filepath: str | Path, layer: int = 0) -> None:
        """Write one layer of this segment out as a 16-bit PCM .wav file."""
        pcm = self.to_pcm16(layer)
        config = self.layer_config(layer)

        with wavefile.open(str(filepath), "wb") as out:
            out.setnchannels(max(1, config.channels))
            out.setsampwidth(2)  # to_pcm16 always yields 16-bit samples
            out.setframerate(config.sample_rate)
            out.writeframes(pcm)

    @override
    def __repr__(self):
        config = self.layer_config() if self.stream.stream_header.layer_infos else None
        codec = "?" if config is None else (
            config.codec.name if config.codec else str(config.codec_uuid)
        )
        rate = 0 if config is None else config.sample_rate
        return (
            f"RWA_StreamSegment(#{self.index} {self.name!r}, codec={codec}, "
            f"sample_rate={rate}, size={self.size()})"
        )


@dataclass
class RWA_Stream(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    stream_header: RWA_Stream_Header = field(default_factory=RWA_Stream_Header)
    stream_data: RWA_Stream_Data = field(default_factory=RWA_Stream_Data)

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RWA_Stream":
        stream = cls()
        stream.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            stream.header,
            RWSectionType.rwaID_STREAM.value,
            "RWA_Stream chunk type",
        )

        stream.stream_header = RWA_Stream_Header.read(parser, parent=stream)
        stream.stream_data = RWA_Stream_Data.read(parser, parent=stream)

        return stream

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        """Serialize the stream back out.

        The header's offsets and block sizes are written as they stand -- this
        round-trips a file and carries metadata edits, but it does not repack
        the data chunk, so replacing a segment's audio means fixing up the
        offsets yourself.
        """
        if isinstance(f, (str, os.PathLike)):
            with open(f, "wb") as out:
                self.write(out, stamp, parent=parent)
            return

        buf = io.BytesIO()

        self.stream_header.write(buf, stamp, parent=self)
        self.stream_data.write(buf, stamp, parent=self)

        payload = buf.getvalue()
        rw_header = RWHeader(
            type=RWSectionType.rwaID_STREAM.value,
            size=len(payload),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(payload)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """The stream file's own name, as stored in the header."""
        return self.stream_header.file_name

    @property
    def segments(self) -> list[RWA_StreamSegment]:
        """Every segment in the file, in header order."""
        return [
            RWA_StreamSegment(self, i)
            for i in range(self.stream_header.total_segments)
        ]

    @property
    def layers(self) -> list[str]:
        """The layer names shared by every segment."""
        return list(self.stream_header.layer_names)

    def segment_names(self) -> list[str]:
        """Every segment's name, in file order."""
        return list(self.stream_header.segment_names)

    def find_segment(self, key: int | str) -> RWA_StreamSegment | None:
        """Look a segment up by index or by name, or None if there is no match.

        An `int` is a position in the segment list and may be negative, counting
        from the end. A `str` is matched against the segment name: exactly
        first, then case-insensitively. Names are unique within the shipped
        files; if one does have duplicates, the earliest wins.

        Args:
            key: Segment index, or segment name.
        """
        names = self.stream_header.segment_names
        count = len(names)

        if isinstance(key, bool):  # bool is an int subclass; reject it explicitly
            raise TypeError("find_segment() expects an index or a name, not a bool")

        if isinstance(key, int):
            if -count <= key < count:
                return RWA_StreamSegment(self, key % count)
            return None

        if isinstance(key, str):
            for i, name in enumerate(names):
                if name == key:
                    return RWA_StreamSegment(self, i)

            folded = key.casefold()
            for i, name in enumerate(names):
                if name.casefold() == folded:
                    return RWA_StreamSegment(self, i)
            return None

        raise TypeError(
            f"find_segment() expects an index or a name, got {type(key).__name__}"
        )

    def get_segment(self, key: int | str) -> RWA_StreamSegment:
        """Like `find_segment`, but raises instead of returning None.

        Args:
            key: Segment index, or segment name.

        Raises:
            IndexError: `key` is an out-of-range index.
            KeyError: `key` is a name that is not in the file.
        """
        found = self.find_segment(key)
        if found is not None:
            return found

        if isinstance(key, int):
            raise IndexError(
                f"segment index {key} out of range "
                f"({self.stream_header.total_segments} segments)"
            )
        raise KeyError(f"no segment named {key!r} in {self.name!r}")

    def __len__(self) -> int:
        return self.stream_header.total_segments

    def __iter__(self) -> Iterator[RWA_StreamSegment]:
        return iter(self.segments)

    def __getitem__(self, key: int | str) -> RWA_StreamSegment:
        return self.get_segment(key)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, (int, str)):
            return False
        return self.find_segment(key) is not None

    # ------------------------------------------------------------------
    # WAV export
    # ------------------------------------------------------------------

    def export_wav(self, key: int | str, filepath: str | Path, layer: int = 0) -> None:
        """Export one segment to a .wav file.

        Args:
            key: Segment index, or segment name.
            filepath: Destination .wav path.
            layer: Which layer to take; files with music stems have several.
        """
        self.get_segment(key).export_wav(filepath, layer=layer)

    def export_all(
        self,
        output_dir: str | Path,
        raise_on_error: bool = True,
        layer: int | None = None,
    ) -> list[Path]:
        """Export every segment to .wav files.

        Files are named `<index>_<segment name>.wav`, so segments stay in file
        order and duplicate names cannot collide on disk. When a file has more
        than one layer and no single `layer` is asked for, every layer is
        written as `<index>_<name>.<layer name>.wav`.

        Args:
            output_dir: Directory to write into (created if needed).
            raise_on_error: Abort on the first segment that cannot be decoded.
                When False, undecodable segments are skipped.
            layer: Export only this layer. Defaults to all of them.

        Returns:
            The paths written.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        layers = (
            [layer] if layer is not None else list(range(self.stream_header.total_layers))
        )
        multi_layer = len(layers) > 1

        written: list[Path] = []
        for segment in self.segments:
            safe = "".join(
                c if c.isalnum() or c in " ._-" else "_" for c in segment.name
            ).strip()
            stem = f"{segment.index}_{safe or 'segment'}"

            for layer_index in layers:
                target = out / (
                    f"{stem}.{self._layer_suffix(layer_index)}.wav"
                    if multi_layer
                    else f"{stem}.wav"
                )
                try:
                    segment.export_wav(target, layer=layer_index)
                except NotImplementedError:
                    if raise_on_error:
                        raise
                    continue
                written.append(target)

        return written

    def _layer_suffix(self, layer_index: int) -> str:
        """A filename-safe tag for a layer, used when exporting every layer."""
        names = self.stream_header.layer_names
        name = names[layer_index] if layer_index < len(names) else ""
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name).strip()
        return safe or f"layer{layer_index}"

    @override
    def __repr__(self):
        return f"RWA_Stream({self.stream_header!r}, {self.stream_data!r})"
