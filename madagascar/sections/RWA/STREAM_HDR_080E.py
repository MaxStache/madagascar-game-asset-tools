import io
import uuid
from dataclasses import dataclass, field
from typing import BinaryIO, override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import (
    RW_Section,
    RWHeader,
    expect_chunk_type_or_raise,
    write_bytes,
    write_u16,
    write_u32,
    write_u8,
)
from madagascar.sections.RWA.WAVESTRUCT_0803 import (
    CodecUUID,
    null_guid,
    read_rwguid,
    resolve_codec,
    rwguid_bytes,
)

# ---------------------------------------------------------------------------
# rwaID_STREAM_HDR (0x80E) -- the table of contents of an audio stream file.
#
# Unlike a wave dictionary (0x809), where each wave carries its own struct and
# its own data chunk, a stream file has ONE data chunk (0x80F) holding every
# sound back to back, and this chunk describes how to cut it up:
#
#   segment  -- one logical sound (a line of dialogue, a music cue). Sits at
#               `segment_offset` inside the data chunk.
#   layer    -- one parallel track within every segment (music stems). Each
#               layer has its own codec/format, shared by all segments.
#
# A segment's audio is therefore (segment, layer) addressed, and the usable
# byte counts are stored as one flat array in that order:
#   seg0/layer0 .. seg0/layerN, seg1/layer0 .. segM/layerN
#
# Body layout (all little-endian on PC/Xbox):
#   +0x00  u32     used_size        bytes of this chunk actually in use
#   +0x04  u32     20               constant across the corpus
#   +0x08  u32     16               constant across the corpus
#   +0x0C  u32     36               constant across the corpus
#   +0x10  u32     name_length      length of `file_name`, null excluded
#   +0x14  void*                    runtime pointer
#   +0x18  void*                    runtime pointer
#   +0x1C  u32     0
#   +0x20  u32     total_segments
#   +0x24  void*                    runtime pointer to the segment array
#   +0x28  u32     total_layers
#   +0x2C  void*                    runtime pointer to the layer array
#   +0x30  u32     block_alignment  0x800 in every shipped file
#   +0x34  u32     block_layers_size
#   +0x38  u32     data_offset      file offset of the sample data (0x800-aligned)
#   +0x3C  u32     0
#   +0x40  RWGUID  file_uuid
#   +0x50  char[]  file_name        padded (see _read_padded_string)
#   then:  segment infos, usable sizes, segment GUIDs, segment names,
#          layer infos, layer configs, layer GUIDs, layer names.
#
# Everything past the last layer name is slack inside the chunk -- usually
# zeroes, sometimes uninitialized memory -- and is kept verbatim in `_trailing`
# so a load/save round-trip is byte-identical.
#
# NOTE: GCN/Wii/X360 builds store this big-endian. Only the little-endian
# layout is handled here, which covers every PC/Xbox file the game ships.
# ---------------------------------------------------------------------------

# Strings in this chunk are null-terminated and padded so the whole block is a
# multiple of this. The padding is not always zeroed.
_STRING_ALIGNMENT = 0x10

# The extra block a DSP-ADPCM (GCN/Wii) layer carries after its codec GUID.
_DSP_BLOCK_SIZE = 0x60


def _read_padded_string(parser: Parser) -> tuple[str, bytes]:
    """Read a null-terminated string padded to `_STRING_ALIGNMENT`.

    Returns:
        (text, padding) -- the padding is returned so it can be written back
        verbatim; real files leave garbage there.
    """
    text = parser.readCString()
    consumed = len(text.encode("latin-1")) + 1  # characters + null terminator
    padding = parser.readBytes((-consumed) % _STRING_ALIGNMENT)
    return text, padding


def _write_padded_string(f: BinaryIO, text: str, padding: bytes) -> None:
    """Write a string the way `_read_padded_string` reads it.

    The original padding is reproduced when it still fits (unchanged string),
    otherwise the block is zero-filled.
    """
    encoded = text.encode("latin-1") + b"\x00"
    write_bytes(f, encoded)

    pad_len = (-len(encoded)) % _STRING_ALIGNMENT
    write_bytes(f, padding if len(padding) == pad_len else b"\x00" * pad_len)


@dataclass
class RWA_StreamSegmentInfo:
    """Where one segment's audio sits inside the data chunk (0x20 bytes)."""

    _unk: bytes = b"\x00" * 0x18  # +0x00  runtime pointers / config
    layers_size: int = 0          # +0x18  sum of every layer's size, padding included
    segment_offset: int = 0       # +0x1C  byte offset into the data chunk

    @staticmethod
    def read(parser: Parser) -> "RWA_StreamSegmentInfo":
        return RWA_StreamSegmentInfo(
            _unk=parser.readBytes(0x18),
            layers_size=parser.readUint32(),
            segment_offset=parser.readUint32(),
        )

    def write(self, f: BinaryIO) -> None:
        write_bytes(f, self._unk)
        write_u32(f, self.layers_size)
        write_u32(f, self.segment_offset)

    @override
    def __repr__(self):
        return (
            f"RWA_StreamSegmentInfo(offset=0x{self.segment_offset:X}, "
            f"layers_size={self.layers_size})"
        )


@dataclass
class RWA_StreamLayerInfo:
    """How one layer's bytes are blocked up inside a segment (0x28 bytes).

    Audio is stored in super-blocks of `block_size` usable bytes, each padded
    out to `block_size_padded` so the streamer can read whole sectors. A layer
    starts `layer_start` bytes into every segment.
    """

    _unk00: int = 0            # +0x00  runtime pointer
    _unk04: int = 0            # +0x04  runtime pointer
    _unk08: int = 0            # +0x08  null
    samples_per_frame: int = 0  # +0x0C
    block_size_padded: int = 0  # +0x10  super-block size including inter-layer padding
    _unk14: int = 0            # +0x14  runtime pointer
    interleave: int = 0        # +0x18  u16
    frame_size: int = 0        # +0x1A  u16, codec frame size per channel
    _unk1C: int = 0            # +0x1C  codec related?
    block_size: int = 0        # +0x20  usable bytes per super-block
    layer_start: int = 0       # +0x24  this layer's offset within a segment

    @staticmethod
    def read(parser: Parser) -> "RWA_StreamLayerInfo":
        return RWA_StreamLayerInfo(
            _unk00=parser.readUint32(),
            _unk04=parser.readUint32(),
            _unk08=parser.readUint32(),
            samples_per_frame=parser.readUint32(),
            block_size_padded=parser.readUint32(),
            _unk14=parser.readUint32(),
            interleave=parser.readUint16(),
            frame_size=parser.readUint16(),
            _unk1C=parser.readUint32(),
            block_size=parser.readUint32(),
            layer_start=parser.readUint32(),
        )

    def write(self, f: BinaryIO) -> None:
        write_u32(f, self._unk00)
        write_u32(f, self._unk04)
        write_u32(f, self._unk08)
        write_u32(f, self.samples_per_frame)
        write_u32(f, self.block_size_padded)
        write_u32(f, self._unk14)
        write_u16(f, self.interleave)
        write_u16(f, self.frame_size)
        write_u32(f, self._unk1C)
        write_u32(f, self.block_size)
        write_u32(f, self.layer_start)

    @override
    def __repr__(self):
        return (
            f"RWA_StreamLayerInfo(block_size={self.block_size}, "
            f"block_size_padded={self.block_size_padded}, "
            f"frame_size={self.frame_size}, layer_start={self.layer_start})"
        )


@dataclass
class RWA_StreamLayerConfig:
    """One layer's audio format (0x2C bytes, plus a DSP block, plus padding)."""

    sample_rate: int = 0     # +0x00
    _unk04: int = 0          # +0x04  runtime pointer
    layer_size: int = 0      # +0x08  at or near the layer's usable size
    bit_depth: int = 0       # +0x0C  u8, bits per sample
    channels: int = 0        # +0x0D  u8
    _unk0E: bytes = b"\x00" * 0x0E  # +0x0E
    codec_uuid: uuid.UUID = field(default_factory=null_guid)  # +0x1C

    # Present only for DSP-ADPCM layers: 0x1C unknown, 0x20 coefs, 0x04 unknown,
    # 0x04 hist, 0x1C unknown -- all big-endian. Kept raw; see the properties.
    dsp_data: bytes = b""

    _pad: bytes = b"\x00" * 4  # trailing padding/garbage after every layer config

    @property
    def codec(self) -> CodecUUID | None:
        """The CodecUUID enum member for this layer, or None if unrecognized."""
        return resolve_codec(self.codec_uuid)

    @property
    def dsp_coefs(self) -> bytes:
        """The 16 big-endian s16 DSP-ADPCM coefficients, or b"" if not DSP."""
        return self.dsp_data[0x1C:0x3C]

    @property
    def dsp_hist(self) -> bytes:
        """The big-endian s16 hist1/hist2 pair, or b"" if not DSP."""
        return self.dsp_data[0x40:0x44]

    @staticmethod
    def read(parser: Parser) -> "RWA_StreamLayerConfig":
        cfg = RWA_StreamLayerConfig(
            sample_rate=parser.readUint32(),
            _unk04=parser.readUint32(),
            layer_size=parser.readUint32(),
            bit_depth=parser.readUint8(),
            channels=parser.readUint8(),
            _unk0E=parser.readBytes(0x0E),
            codec_uuid=read_rwguid(parser),
        )

        if cfg.codec is CodecUUID.DSPADPCM:
            cfg.dsp_data = parser.readBytes(_DSP_BLOCK_SIZE)

        cfg._pad = parser.readBytes(4)

        return cfg

    def write(self, f: BinaryIO) -> None:
        write_u32(f, self.sample_rate)
        write_u32(f, self._unk04)
        write_u32(f, self.layer_size)
        write_u8(f, self.bit_depth)
        write_u8(f, self.channels)
        write_bytes(f, self._unk0E)
        write_bytes(f, rwguid_bytes(self.codec_uuid))

        if self.codec is CodecUUID.DSPADPCM:
            write_bytes(f, self.dsp_data)

        write_bytes(f, self._pad)

    @override
    def __repr__(self):
        codec = self.codec.name if self.codec else str(self.codec_uuid)
        return (
            f"RWA_StreamLayerConfig(codec=<CodecUUID.{codec}>, "
            f"sample_rate={self.sample_rate}, bit_depth={self.bit_depth}, "
            f"channels={self.channels})"
        )


@dataclass
class RWA_Stream_Header(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    # -- base header (see the layout comment above) --
    used_size: int = 0        # +0x00
    _unk04: int = 20          # +0x04
    _unk08: int = 16          # +0x08
    _unk0C: int = 36          # +0x0C
    _name_length: int = 0     # +0x10  re-derived from file_name on write
    _unk14: int = 0           # +0x14
    _unk18: int = 0           # +0x18
    _unk1C: int = 0           # +0x1C
    _segments_ptr: int = 0    # +0x24
    _layers_ptr: int = 0      # +0x2C
    block_alignment: int = 0x800   # +0x30
    block_layers_size: int = 0     # +0x34
    data_offset: int = 0           # +0x38
    _unk3C: int = 0                # +0x3C
    file_uuid: uuid.UUID = field(default_factory=null_guid)  # +0x40
    file_name: str = ""            # +0x50
    _file_name_pad: bytes = b""

    # -- per-segment tables (all `total_segments` long) --
    segments: list[RWA_StreamSegmentInfo] = field(default_factory=list)
    segment_uuids: list[uuid.UUID] = field(default_factory=list)
    segment_names: list[str] = field(default_factory=list)
    _segment_name_pads: list[bytes] = field(default_factory=list)

    # Usable (unpadded) byte count per (segment, layer), segment-major.
    usable_sizes: list[int] = field(default_factory=list)

    # -- per-layer tables (all `total_layers` long) --
    layer_infos: list[RWA_StreamLayerInfo] = field(default_factory=list)
    layer_configs: list[RWA_StreamLayerConfig] = field(default_factory=list)
    layer_uuids: list[uuid.UUID] = field(default_factory=list)
    layer_names: list[str] = field(default_factory=list)
    _layer_name_pads: list[bytes] = field(default_factory=list)

    _trailing: bytes = b""  # slack after the last layer name

    @property
    def total_segments(self) -> int:
        return len(self.segments)

    @property
    def total_layers(self) -> int:
        return len(self.layer_infos)

    def usable_size(self, segment_index: int, layer_index: int = 0) -> int:
        """Usable bytes of one (segment, layer) pair."""
        return self.usable_sizes[segment_index * self.total_layers + layer_index]

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RWA_Stream_Header":
        stream_header = cls()
        stream_header.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            stream_header.header,
            RWSectionType.rwaID_STREAM_HDR.value,
            "RWA_Stream_Header chunk type",
        )

        # The chunk is bigger than its contents (see `used_size`), so parse from
        # a view of the body and sweep whatever is left into `_trailing`.
        p = Parser(parser.read(stream_header.header.size), endian="little")

        stream_header.used_size = p.readUint32()
        stream_header._unk04 = p.readUint32()
        stream_header._unk08 = p.readUint32()
        stream_header._unk0C = p.readUint32()
        stream_header._name_length = p.readUint32()
        stream_header._unk14 = p.readUint32()
        stream_header._unk18 = p.readUint32()
        stream_header._unk1C = p.readUint32()
        total_segments = p.readUint32()
        stream_header._segments_ptr = p.readUint32()
        total_layers = p.readUint32()
        stream_header._layers_ptr = p.readUint32()
        stream_header.block_alignment = p.readUint32()
        stream_header.block_layers_size = p.readUint32()
        stream_header.data_offset = p.readUint32()
        stream_header._unk3C = p.readUint32()
        stream_header.file_uuid = read_rwguid(p)

        stream_header.file_name, stream_header._file_name_pad = _read_padded_string(p)

        stream_header.segments = [
            RWA_StreamSegmentInfo.read(p) for _ in range(total_segments)
        ]

        stream_header.usable_sizes = [
            p.readUint32() for _ in range(total_segments * total_layers)
        ]

        stream_header.segment_uuids = [read_rwguid(p) for _ in range(total_segments)]

        stream_header.segment_names = []
        stream_header._segment_name_pads = []
        for _ in range(total_segments):
            name, pad = _read_padded_string(p)
            stream_header.segment_names.append(name)
            stream_header._segment_name_pads.append(pad)

        stream_header.layer_infos = [
            RWA_StreamLayerInfo.read(p) for _ in range(total_layers)
        ]
        stream_header.layer_configs = [
            RWA_StreamLayerConfig.read(p) for _ in range(total_layers)
        ]

        stream_header.layer_uuids = [read_rwguid(p) for _ in range(total_layers)]

        stream_header.layer_names = []
        stream_header._layer_name_pads = []
        for _ in range(total_layers):
            name, pad = _read_padded_string(p)
            stream_header.layer_names.append(name)
            stream_header._layer_name_pads.append(pad)

        stream_header._trailing = p.readRemaining()

        return stream_header

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        # The counts drive the reader's loops, so derive them from the lists
        # rather than trusting fields left stale by an edit. `used_size` and
        # the offsets cannot be re-derived (the shipped values do not match any
        # obvious sum), so they are written back as they stand -- resizing a
        # name or a segment means fixing those up yourself.
        total_segments = self.total_segments
        total_layers = self.total_layers

        write_u32(buf, self.used_size)
        write_u32(buf, self._unk04)
        write_u32(buf, self._unk08)
        write_u32(buf, self._unk0C)
        write_u32(buf, len(self.file_name.encode("latin-1")))
        write_u32(buf, self._unk14)
        write_u32(buf, self._unk18)
        write_u32(buf, self._unk1C)
        write_u32(buf, total_segments)
        write_u32(buf, self._segments_ptr)
        write_u32(buf, total_layers)
        write_u32(buf, self._layers_ptr)
        write_u32(buf, self.block_alignment)
        write_u32(buf, self.block_layers_size)
        write_u32(buf, self.data_offset)
        write_u32(buf, self._unk3C)
        write_bytes(buf, rwguid_bytes(self.file_uuid))

        _write_padded_string(buf, self.file_name, self._file_name_pad)

        for segment in self.segments:
            segment.write(buf)

        for size in self.usable_sizes:
            write_u32(buf, size)

        for guid in self.segment_uuids:
            write_bytes(buf, rwguid_bytes(guid))

        for i, name in enumerate(self.segment_names):
            pad = self._segment_name_pads[i] if i < len(self._segment_name_pads) else b""
            _write_padded_string(buf, name, pad)

        for info in self.layer_infos:
            info.write(buf)

        for config in self.layer_configs:
            config.write(buf)

        for guid in self.layer_uuids:
            write_bytes(buf, rwguid_bytes(guid))

        for i, name in enumerate(self.layer_names):
            pad = self._layer_name_pads[i] if i < len(self._layer_name_pads) else b""
            _write_padded_string(buf, name, pad)

        write_bytes(buf, self._trailing)

        payload = buf.getvalue()
        rw_header = RWHeader(
            type=RWSectionType.rwaID_STREAM_HDR.value,
            size=len(payload),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(payload)

    @override
    def __repr__(self):
        return (
            f"RWA_Stream_Header(file_name={self.file_name!r}, "
            f"segments={self.total_segments}, layers={self.total_layers}, "
            f'uuid="{self.file_uuid}")'
        )
