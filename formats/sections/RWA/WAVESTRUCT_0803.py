from enum import Enum
import io
import uuid
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import (
    RW_Section,
    RWHeader,
    expect_chunk_type_or_raise,
    _write_u8,
    _write_u16,
    _write_u32,
    _write_bytes,
)

# ---------------------------------------------------------------------------
# Layout reverse-engineered from Game.exe (Madagascar):
#   RtWave_StreamRead        @ 0x00508b80  (reads chunk 0x803 struct + 0x804 data)
#   RtWave_CreateFromStruct  @ 0x00508df0  (parses the 0x803 struct body below)
#   RtWaveFormat size calc   @ 0x0050a290  (FUN_0050a290)
#
# The 0x803 "wave struct" body is:
#   u32          flags               (presence bitmask, see FLAG_HAS_*)
#   RtWaveFormat source_format       (format the sample data is stored in)
#   RtWaveFormat dest_format         (format it decodes to; == source when uncompressed)
#   u32          loop_stream_flag
#   [flags & 0x1]  16-byte identifier GUID
#   [flags & 0x2]  stream name (null-terminated, padded to _NAME_ALIGNMENT)
#   [flags & 0x4]  16-byte codec/decoder class GUID
#   [flags & 0x8]  16-byte auxiliary class GUID
#
# NOTE: RenderWare GUIDs store Data1/2/3 little-endian on disk, so they must be
#       decoded with uuid.UUID(bytes_le=...) (NOT bytes=...) to read correctly.
# ---------------------------------------------------------------------------

# Name blocks are padded to this alignment (RwAudio alloc alignment, DAT_006322c0
# in Game.exe -- runtime-initialized, so read as 0 statically; value 16 verified
# from real wave structs, e.g. an 18-char name occupies a 32-byte field).
_NAME_ALIGNMENT = 16

# Presence bits in the wave-struct `flags` field. Each set bit appends a block
# AFTER the two format descriptors, in ascending bit order.
FLAG_HAS_IDENTIFIER = 0x1  # 16-byte wave-instance GUID
FLAG_HAS_NAME       = 0x2  # null-terminated name, padded to _NAME_ALIGNMENT
FLAG_HAS_CODEC      = 0x4  # 16-byte codec/decoder class GUID
FLAG_HAS_AUX        = 0x8  # 16-byte auxiliary class GUID

# fmt: off
class CodecUUID(Enum):
    PCM16    = uuid.UUID("D01BD217-3587-4EED-B9D9-B8E86EA9B995")  # PCM Signed 16-bit
    PSXADPCM = uuid.UUID("D9EA9798-BBBC-447B-96B2-654759102E16")  # PSX-ADPCM
    DSPADPCM = uuid.UUID("F86215B0-31D5-4C29-BD37-CDBF9BD10C53")  # DSP-ADPCM (GCN/Wii)
    XBOXIMA  = uuid.UUID("632FA22B-11DD-458F-AA27-A5C346E9790E")  # Xbox IMA ADPCM
    IMAADPCM = uuid.UUID("EF386593-B611-432D-957F-A71ADE44227A")  # IMA ADPCM (PC)
    FLOAT    = uuid.UUID("DA1E4382-2C99-4C61-AD99-7F364B211537")  # Float
    WMA      = uuid.UUID("3F1D8147-B7C4-41E6-A69B-3CC0025B33C7")  # WMA
    MP3      = uuid.UUID("BACFB36E-529D-4692-BF53-324256B0734F")  # MP3
    MP2      = uuid.UUID("34D09A54-57D3-409E-A6AD-2BC845AEC339")  # MP2
    MP1      = uuid.UUID("04C15BA7-F907-40AB-A49F-EEFEF8C4D296")  # MP1
    AC3      = uuid.UUID("A30DB390-58A9-43C4-B9D2-55D84D3AE754")  # AC3
# fmt: on


def _read_rwguid(parser: Parser) -> uuid.UUID:
    """Read a 16-byte RenderWare GUID (Data1/2/3 little-endian on disk)."""
    return uuid.UUID(bytes_le=parser.readBytes(16))


def _rwguid_bytes(value: uuid.UUID) -> bytes:
    return value.bytes_le


def resolve_codec(guid: uuid.UUID):
    """Return the matching CodecUUID enum member, or None if unknown."""
    if guid is None:
        return None
    try:
        return CodecUUID(guid)
    except ValueError:
        return None


@dataclass
class RWA_WaveFormat:
    """RenderWare Audio format descriptor (RtWaveFormat).

    On disk: 0x1C (28) byte base, +16 for the codec GUID when present, plus
    optional aux data (misc/codec tables) when present. Parsed and sized by
    FUN_0050a2b0 / FUN_0050a290 in Game.exe.
    """

    sample_rate: int = 0        # u32  +0x00
    _format_ref: int = 0        # u32  +0x04  runtime ptr on disk; nonzero => codec GUID present
    data_size: int = 0          # u32  +0x08  size of the sample data in bytes
    bit_depth: int = 0          # u8   +0x0C  bits per sample
    channels: int = 0           # u8   +0x0D
    _pad0: int = 0              # u16  +0x0E
    _aux_ref: int = 0           # u32  +0x10  runtime ptr on disk; nonzero => aux data present
    aux_size: int = 0           # u32  +0x14  size of aux/codec data
    _tail: bytes = b"\x00\x00\x00\x00"  # +0x18  (u8 flags, u8, u16 pad) kept verbatim
    codec_uuid: uuid.UUID = None        # +0x1C  16-byte GUID (present when _format_ref != 0)
    aux_data: bytes = b""               # aux_size bytes (present when _aux_ref != 0)

    @property
    def codec(self):
        """The CodecUUID enum member for this format, or None if unrecognized."""
        return resolve_codec(self.codec_uuid)

    @staticmethod
    def read(parser: Parser) -> "RWA_WaveFormat":
        fmt = RWA_WaveFormat()
        fmt.sample_rate = parser.readUint32()
        fmt._format_ref = parser.readUint32()
        fmt.data_size = parser.readUint32()
        fmt.bit_depth = parser.readUint8()
        fmt.channels = parser.readUint8()
        fmt._pad0 = parser.readUint16()
        fmt._aux_ref = parser.readUint32()
        fmt.aux_size = parser.readUint32()
        fmt._tail = parser.readBytes(4)

        if fmt._format_ref != 0:
            fmt.codec_uuid = _read_rwguid(parser)
        if fmt._aux_ref != 0:
            fmt.aux_data = parser.readBytes(fmt.aux_size)

        return fmt

    def write(self, f):
        _write_u32(f, self.sample_rate)
        _write_u32(f, self._format_ref)
        _write_u32(f, self.data_size)
        _write_u8(f, self.bit_depth)
        _write_u8(f, self.channels)
        _write_u16(f, self._pad0)
        _write_u32(f, self._aux_ref)
        _write_u32(f, self.aux_size)
        _write_bytes(f, self._tail)

        if self._format_ref != 0:
            _write_bytes(f, _rwguid_bytes(self.codec_uuid))
        if self._aux_ref != 0:
            _write_bytes(f, self.aux_data)

    def __repr__(self):
        codec = self.codec.name if self.codec else (
            str(self.codec_uuid) if self.codec_uuid else "None"
        )
        return (
            f"RWA_WaveFormat(codec=<CodecUUID.{codec}>, sample_rate={self.sample_rate}, "
            f"bit_depth={self.bit_depth}, channels={self.channels}, "
            f"data_size={self.data_size}, aux_size={self.aux_size})"
        )


@dataclass
class RWA_WaveStruct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    flags: int = 0  # u32 presence bitmask (see FLAG_HAS_*)

    source_format: RWA_WaveFormat = field(default_factory=RWA_WaveFormat)  # stored data
    dest_format: RWA_WaveFormat = field(default_factory=RWA_WaveFormat)    # decoded PCM

    loop_stream_flag: int = 0  # u32

    identifier_uuid: uuid.UUID = None  # flags & FLAG_HAS_IDENTIFIER (wave-instance GUID)
    stream_name: str = ""              # flags & FLAG_HAS_NAME
    _name_padding: bytes = b""         # padding after the name (kept for exact round-trip)
    decoder_uuid: uuid.UUID = None     # flags & FLAG_HAS_CODEC (codec/decoder class GUID)
    aux_uuid: uuid.UUID = None         # flags & FLAG_HAS_AUX (auxiliary class GUID)

    _trailing: bytes = b""  # any bytes after the parsed fields (normally empty)

    # -- convenience accessors (source format describes the stored samples) --
    @property
    def sample_rate(self) -> int:
        return self.source_format.sample_rate

    @property
    def stream_size(self) -> int:
        return self.source_format.data_size

    @property
    def bit_depth(self) -> int:
        return self.source_format.bit_depth

    @property
    def channels(self) -> int:
        return self.source_format.channels

    @property
    def codec_uuid(self) -> uuid.UUID:
        return self.source_format.codec_uuid

    @property
    def codec(self):
        return self.source_format.codec

    @staticmethod
    def read(parser: Parser, parent=None) -> "RWA_WaveStruct":
        wavestruct = RWA_WaveStruct()
        wavestruct.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            wavestruct.header,
            RWSectionType.rwaID_WAVESTRUCT.value,
            "RWA_WaveStruct chunk type",
        )

        #parser = Parser(orig_parser.read(wavestruct.header.size), endian="little")

        wavestruct.flags = parser.readUint32()
        wavestruct.source_format = RWA_WaveFormat.read(parser)
        wavestruct.dest_format = RWA_WaveFormat.read(parser)
        wavestruct.loop_stream_flag = parser.readUint32()

        if wavestruct.flags & FLAG_HAS_IDENTIFIER:
            wavestruct.identifier_uuid = _read_rwguid(parser)

        if wavestruct.flags & FLAG_HAS_NAME:
            start = parser.tell()
            wavestruct.stream_name = parser.readCString()
            consumed = parser.tell() - start  # name + null terminator
            pad_len = (-consumed) % _NAME_ALIGNMENT
            wavestruct._name_padding = parser.readBytes(pad_len)

        if wavestruct.flags & FLAG_HAS_CODEC:
            wavestruct.decoder_uuid = _read_rwguid(parser)

        if wavestruct.flags & FLAG_HAS_AUX:
            wavestruct.aux_uuid = _read_rwguid(parser)

        #wavestruct._trailing = parser.readRemaining()

        return wavestruct

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        _write_u32(buf, this.flags)
        this.source_format.write(buf)
        this.dest_format.write(buf)
        _write_u32(buf, this.loop_stream_flag)

        if this.flags & FLAG_HAS_IDENTIFIER:
            _write_bytes(buf, _rwguid_bytes(this.identifier_uuid))

        if this.flags & FLAG_HAS_NAME:
            encoded = this.stream_name.encode("latin-1") + b"\x00"
            _write_bytes(buf, encoded)
            pad_len = (-len(encoded)) % _NAME_ALIGNMENT
            # Reproduce the original padding verbatim when the name is unchanged
            # (real files carry non-zero garbage there); otherwise zero-fill.
            if len(this._name_padding) == pad_len:
                _write_bytes(buf, this._name_padding)
            else:
                _write_bytes(buf, b"\x00" * pad_len)

        if this.flags & FLAG_HAS_CODEC:
            _write_bytes(buf, _rwguid_bytes(this.decoder_uuid))

        if this.flags & FLAG_HAS_AUX:
            _write_bytes(buf, _rwguid_bytes(this.aux_uuid))

        _write_bytes(buf, this._trailing)

        payload = buf.getvalue()
        rw_header = RWHeader(
            type=RWSectionType.rwaID_WAVESTRUCT.value,
            size=len(payload),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(payload)

    def __repr__(self):
        return (
            f"RWA_WaveStruct(name={self.stream_name!r}, flags=0x{self.flags:X}, "
            f"source={self.source_format!r}, dest={self.dest_format!r}, "
            f"loop_stream_flag={self.loop_stream_flag}, "
            f"identifier=\"{self.identifier_uuid}\", decoder=\"{self.decoder_uuid}\", "
            f"aux=\"{self.aux_uuid}\")"
        )
