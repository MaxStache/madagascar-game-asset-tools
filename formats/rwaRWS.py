"""
rwaRWS.py — RenderWare Audio Stream (.RWS) Library
========================================================

Read, write, decode, and encode Renderware Audio RWS files.
Uses Pillow for PNG import/export.

Usage:
    import rwaRWS

    # Read
    rws = rwaRWS.load("file.rws")
    for stream in rwaRWS.stream:
        print(tex.name, tex.width, tex.height)

    # Decode to RGBA
    rgba = rwtxd.decode(tex)

    # Export to PNG
    rwtxd.export_png(tex, "output.png")

    # Create from scratch
    txd = rwtxd.TextureDictionary()
    tex = rwtxd.create_texture("mytex", rgba_bytes, 64, 64)
    txd.textures.append(tex)
    rwtxd.save(txd, "output.txd")

    # Import from PNG
    tex = rwtxd.import_png("input.png", name="mytex")
"""

import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union
from enum import Enum
from lib.parser import Parser
import wave
import tkinter as tk
from tkinter import ttk

__version__ = "1.0.0"


# ═══════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════

DEFAULT_VERSION_STAMP = 0x3700021C

CHUNK_RWSSTREAM_2057 = 0x809
CHUNK_RWSSTREAM_2057_FILE_HEADER = 0x80A
CHUNK_RWSSTREAM_2057_FILE_DATA = 0x80C
CHUNK_RWSSTREAM_2057_STREAM = 0x802
CHUNK_RWSSTREAM_2057_STREAM_HEADER = 0x803
CHUNK_RWSSTREAM_2057_STREAM_DATA = 0x804

PCM16_UUID_REST = bytes.fromhex("87 35 ED 4E B9 D9 B8 E8 6E A9 B9 95")


class CodecUUID(Enum):
    PCM16 = 0xD01BD217  # {D01BD217-3587-4EED-B9D9-B8E86EA9B995} PCM Signed 16-bit
    PSXADPCM = 0xD9EA9798  # {D9EA9798-BBBC-447B-96B2-654759102E16} PSX-ADPCM
    DSPADPCM = 0xF86215B0  # {F86215B0-31D5-4C29-BD37-CDBF9BD10C53} DSP-ADPCM (GCN/Wii)
    XBOXIMA = 0x632FA22B  # {632FA22B-11DD-458F-AA27-A5C346E9790E} Xbox IMA ADPCM
    IMAADPCM = 0xEF386593  # {EF386593-B611-432D-957F-A71ADE44227A} IMA ADPCM (PC)
    FLOAT = 0xDA1E4382  # {DA1E4382-2C99-4C61-AD99-7F364B211537} Float
    WMA = 0x3F1D8147  # {3F1D8147-B7C4-41E6-A69B-3CC0025B33C7} WMA
    MP3 = 0xBACFB36E  # {BACFB36E-529D-4692-BF53-324256B0734F} MP3
    MP2 = 0x34D09A54  # {34D09A54-57D3-409E-A6AD-2BC845AEC339} MP2
    MP1 = 0x04C15BA7  # {04C15BA7-F907-40AB-A49F-EEFEF8C4D296} MP1
    AC3 = 0xA30DB390  # {A30DB390-58A9-43C4-B9D2-55D84D3AE754} AC3


def read_codec_uuid(parser: Parser):
    value = parser.readUint32()
    return CodecUUID._value2member_map_.get(value, value)


def write_codec_uuid(f, codec: CodecUUID):
    f.write(codec.value.to_bytes(4, byteorder="little"))


# ═══════════════════════════════════════════════════════
#  Data Structures
# ═══════════════════════════════════════════════════════


@dataclass
class RWHeader:
    type: int = 0
    size: int = 0
    library_id_stamp: int = None

    def pack(self) -> bytes:
        return struct.pack("<III", self.type, self.size, self.library_id_stamp)

    @staticmethod
    def read(parser: Parser) -> "RWHeader":
        read_header = parser.readRWChunkHeader()
        return RWHeader(
            type=read_header["id"],
            size=read_header["size"],
            library_id_stamp=read_header["version"],
        )

    @property
    def version(self) -> str:
        if self.library_id_stamp & 0xFFFF0000:
            v = (self.library_id_stamp >> 14 & 0x3FF00) + 0x30000
            v |= self.library_id_stamp >> 16 & 0x3F
            return f"{(v >> 16) & 0xF}.{(v >> 12) & 0xF}.{(v >> 8) & 0xF}.{v & 0xFF}"
        return "3.1.0.0"


@dataclass
class AudioStream_2057_StreamHeader:
    header: RWHeader = field(default_factory=RWHeader)

    _unk1: bytes = b"\x0f\x00\x00\x00"  # Unknown of 4 bytes always15?
    sample_rate: int = 0  # uint32
    _unk2: bytes = b"\x58\xb4\x45\x00"  # Unknown of 4 bytes
    stream_size: int = 0  # uint32
    bit_depth: int = 0  # uint8
    channels: int = 0  # uint8

    _pad1: bytes = b"\x12\x00"  # Unknown of 2 bytes always 18 as uint16? (padding to align to 2 bytes)

    _unk_misc_offset: int = 0  # uint32
    misc_data_size: int = 0  # uint32
    _unk3: int = 0  # uint32

    codec_uuid: CodecUUID = None
    codec_uuid_rest: bytes = b""  # Rest of the uuid (16-4 = 12 bytes)

    input_misc_data: bytes = b""  # misc_data_size bytes
    output_misc_data: bytes = b""  # misc_data_size bytes

    format_info: bytes = b""  # 0x40 bytes

    stream_name: str = ""  # null-terminated string

    _pad2: bytes = (
        b""  # Padding to align to (12 + header.size) - current_position_in_stream
    )

    def write(this, f, stamp, data_size):
        buf = io.BytesIO()

        # _unk1 (padded to 4)
        if len(this._unk1) > 4:
            raise ValueError("_unk1 too large")
        buf.write(this._unk1)
        if 4 - len(this._unk1) > 0:
            buf.write(b"\x00" * (4 - len(this._unk1)))
        # sample_rate
        _write_u32(buf, this.sample_rate)
        # _unk2 (padded to 4)
        if len(this._unk2) > 4:
            raise ValueError("_unk2 too large")
        buf.write(this._unk2)
        if 4 - len(this._unk2) > 0:
            buf.write(b"\x00" * (4 - len(this._unk2)))
        # stream_size
        _write_u32(buf, data_size)
        # bit_depth
        _write_u8(buf, this.bit_depth)
        # channels
        _write_u8(buf, this.channels)

        # _pad1
        if len(this._pad1) > 2:
            raise ValueError("_pad1 too large")
        buf.write(this._pad1)
        if 2 - len(this._pad1) > 0:
            buf.write(b"\x00" * (2 - len(this._pad1)))

        # _unk_misc_offset (offset from start of stream header chunk)
        misc_offset = this._unk_misc_offset
        if misc_offset == 0 and this.misc_data_size > 0:
            misc_offset = 0x3C
        _write_u32(buf, misc_offset)
        # misc_data_size
        _write_u32(buf, this.misc_data_size)
        # _unk3
        _write_u32(buf, this._unk3)

        # codec_uuid
        write_codec_uuid(buf, this.codec_uuid)
        # codec_uuid_rest
        if len(this.codec_uuid_rest) > 12:
            raise ValueError("codec_uuid_rest too large")
        _write_bytes(buf, this.codec_uuid_rest)
        if 12 - len(this.codec_uuid_rest) > 0:
            buf.write(b"\x00" * (12 - len(this.codec_uuid_rest)))

        # input_misc_data
        buf.write(this.input_misc_data)
        # output_misc_data
        buf.write(this.output_misc_data)

        # format_info
        buf.write(this.format_info)
        if 64 - len(this.format_info) > 0:
            buf.write(b"\x00" * (64 - len(this.format_info)))

        # stream_name
        _write_fixed_string(buf, this.stream_name, len(this.stream_name) + 1)
        
        # ALIGN TO 4 BYTES
        while (buf.tell() % 4) != 0:
            buf.write(b"\x00")
        
        
        # _pad2
        current_size = 12 + buf.tell()  # 12 bytes for the chunk header
        padding_needed = (this.header.size + 12) - current_size
        if padding_needed > 0:
            buf.write(b"\x00" * padding_needed)

        rw_header = RWHeader(
            CHUNK_RWSSTREAM_2057_STREAM_HEADER, len(buf.getvalue()), stamp
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class AudioStream_2057_StreamData:
    header: RWHeader = field(default_factory=RWHeader)
    data: bytes = b""  # header.size

    def write(this, f, stamp):
        rw_header = RWHeader(
            CHUNK_RWSSTREAM_2057_STREAM_DATA,
            len(this.data),
            stamp,
        )
        f.write(rw_header.pack())
        f.write(this.data)


@dataclass
class AudioStream_2057_Stream:
    header: RWHeader = field(default_factory=RWHeader)

    header_info: AudioStream_2057_StreamHeader = field(
        default_factory=AudioStream_2057_StreamHeader
    )

    stream_data: AudioStream_2057_StreamData = field(
        default_factory=AudioStream_2057_StreamData
    )

    def write(this, f, stamp):
        buf = io.BytesIO()

        this.header_info.write(buf, stamp, len(this.stream_data.data))
        this.stream_data.write(buf, stamp)

        rw_header = RWHeader(
            CHUNK_RWSSTREAM_2057_STREAM,
            len(buf.getvalue()),
            stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    def export_wav(this, filename):
        header = this.header_info

        codec = header.codec_uuid

        if codec != CodecUUID.PCM16:
            raise NotImplementedError(f"Codec {codec} not supported for writing")

        with wave.open(filename, "wb") as wav_file:
            wav_file.setnchannels(header.channels)
            wav_file.setsampwidth(header.bit_depth // 8)
            wav_file.setframerate(header.sample_rate)
            wav_file.writeframes(this.stream_data.data)


@dataclass
class AudioStream_2057_Data:
    data_header: RWHeader = field(default_factory=RWHeader)

    total_subsongs: int = 0
    subsongs: list[AudioStream_2057_Stream] = field(default_factory=list)

    def write(this, f, stamp):
        buf = io.BytesIO()
        _write_u32(buf, len(this.subsongs))
        for stream in this.subsongs:
            stream.write(buf, stamp)

        rws_header = RWHeader(
            CHUNK_RWSSTREAM_2057_FILE_DATA, len(buf.getvalue()), stamp
        )
        f.write(rws_header.pack())
        f.write(buf.getvalue())


@dataclass
class AudioStream_2057:
    header: RWHeader = field(default_factory=RWHeader)

    # --File Header--
    file_header: RWHeader = field(default_factory=RWHeader)
    _unk1: bytes = b""  # 0x34 bytes
    name: str = ""  # null-terminated string
    _unk2: bytes = b""  # file_header.size - 0x34 - len(name) -1

    # --File Data--
    file_data: "AudioStream_2057_Data" = field(default_factory=AudioStream_2057_Data)

    def __post_init__(self):
        self._unk2 = b"\x00" * (self.file_header.size - 0x34 - len(self.name) - 1)
        
    def replace_subsong(this, index: int, new_stream: AudioStream_2057_Stream):
        if index < 0 or index >= len(this.file_data.subsongs):
            raise IndexError("Subsong index out of range")
        this.file_data.subsongs[index] = new_stream

    def present_streams(self):
        def _format_duration(seconds: float) -> str:
            if seconds <= 0:
                return "n/a"

            total_milliseconds = int(round(seconds * 1000))
            milliseconds = total_milliseconds % 1000
            total_seconds = total_milliseconds // 1000
            seconds_part = total_seconds % 60
            total_minutes = total_seconds // 60
            minutes = total_minutes % 60
            hours = total_minutes // 60

            if hours:
                return f"{hours}:{minutes:02d}:{seconds_part:02d}.{milliseconds // 10}"
            return f"{minutes}:{seconds_part:02d}.{milliseconds // 10}"

        root = tk.Tk()
        root.title("RWS Streams")
        root.geometry("500x630")

        # Create Treeview
        tree = ttk.Treeview(
            root, columns=("Index", "Name", "SampleRate", "Length"), show="headings"
        )

        # Define headings
        tree.heading("Index", text="#")
        tree.heading("Name", text="Name")
        tree.heading("SampleRate", text="Sample Rate")
        tree.heading("Length", text="Length")

        # Define column widths
        tree.column("Index", width=50, anchor="center")
        tree.column("Name", width=150)
        tree.column("SampleRate", width=40, anchor="center")
        tree.column("Length", width=60, anchor="center")

        for i, stream in enumerate(self.file_data.subsongs):
            name = stream.header_info.stream_name
            sample_rate = stream.header_info.sample_rate
            channels = stream.header_info.channels
            bit_depth = stream.header_info.bit_depth
            bytes_per_sample = max(1, bit_depth // 8)
            bytes_per_frame = channels * bytes_per_sample
            stream_length = len(stream.stream_data.data)
            duration_seconds = (
                stream_length / (sample_rate * bytes_per_frame)
                if sample_rate > 0 and bytes_per_frame > 0
                else 0
            )

            tree.insert(
                "",
                tk.END,
                values=(i, name, sample_rate, _format_duration(duration_seconds)),
            )

        tree.pack(fill="both", expand=True)

        root.mainloop()

    def getSubstream(self, index: int) -> AudioStream_2057_Stream:
        if index < 0 or index >= len(self.file_data.subsongs):
            raise IndexError("Substream index out of range")
        return self.file_data.subsongs[index]

    def save(this, filepath: Union[str, Path]):
        _write_2057(this, filepath)


# ═══════════════════════════════════════════════════════
#  Binary I/O helpers
# ═══════════════════════════════════════════════════════


def _write_u8(f, v):
    f.write(struct.pack("<B", v))


def _write_u16(f, v):
    f.write(struct.pack("<H", v))


def _write_u32(f, v):
    f.write(struct.pack("<I", v))


def _write_bytes(f, data):
    f.write(data)


def _read_fixed_string(f, length: int) -> str:
    raw = f.read(length)
    null = raw.find(b"\x00")
    return (raw[:null] if null >= 0 else raw).decode("ascii", errors="replace")


def _write_fixed_string(f, s: str, length: int):
    encoded = s.encode("ascii", errors="replace")[: length - 1]
    f.write(encoded + b"\x00" * (length - len(encoded)))


def _write_header(f, chunk_type: int, size: int, stamp: int = None):
    f.write(struct.pack("<III", chunk_type, size, stamp))


def expect_chunk_type_or_raise(
    header: RWHeader, expected_type: int, error: str = "Wrong Chunk Type"
):
    if header.type != expected_type:
        raise ValueError(
            f"{error}: expected 0x{expected_type:02X}, got 0x{header.type:02X} ({int(header.type)})"
        )

def _import_wav_getData(filepath: Union[str, Path]) -> tuple[bytes, int, int, int]:
    with wave.open(filepath, "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        bit_depth = wav_file.getsampwidth() * 8
        frames = wav_file.getnframes()
        audio_data = wav_file.readframes(frames)

    if channels != 1:
        if bit_depth != 16:
            raise ValueError("Only 16-bit PCM can be downmixed to mono")

        from array import array
        import sys

        samples = array("h")
        samples.frombytes(audio_data)
        if sys.byteorder != "little":
            samples.byteswap()

        mono = array("h")
        for i in range(0, len(samples), channels):
            frame = samples[i : i + channels]
            mono.append(int(sum(frame) / channels))

        if sys.byteorder != "little":
            mono.byteswap()

        audio_data = mono.tobytes()
        channels = 1

    return audio_data, sample_rate, bit_depth, channels

def import_wav(filepath: Union[str, Path], name: str = "imported") -> AudioStream_2057_Stream:
    audio_data, sample_rate, bit_depth, channels = _import_wav_getData(filepath)
    
    stream = AudioStream_2057_Stream()
    
    stream.header_info = AudioStream_2057_StreamHeader(
        sample_rate=sample_rate,
        channels=channels,
        bit_depth=bit_depth,
        stream_size=len(audio_data),
        codec_uuid=CodecUUID.PCM16,
        codec_uuid_rest=PCM16_UUID_REST,
        stream_name=name,
    )

    stream.stream_data = AudioStream_2057_StreamData(data=audio_data)

    return stream

def _2057_read_stream_chunk_header(parser: Parser) -> AudioStream_2057_StreamHeader:
    sh = AudioStream_2057_StreamHeader()

    sh.header = RWHeader.read(parser)

    expect_chunk_type_or_raise(
        sh.header,
        CHUNK_RWSSTREAM_2057_STREAM_HEADER,
        "Not a 2057 RWS (STREAM_HEADER)",
    )

    sh._unk1 = parser.readBytes(4)  # Always 15!?
    sh.sample_rate = parser.readUint32()
    sh._unk2 = parser.readBytes(4)  # Always 4568152!?
    sh.stream_size = parser.readUint32()
    sh.bit_depth = parser.readUint8()
    sh.channels = parser.readUint8()

    sh._pad1 = parser.readBytes(2)  # Always 18 as uint!?
    sh._unk_misc_offset = parser.readUint32()
    sh.misc_data_size = parser.readUint32()
    sh._unk3 = parser.readUint32()  # Always 0!?

    sh.codec_uuid = read_codec_uuid(parser)
    sh.codec_uuid_rest = parser.readBytes(12)

    sh.input_misc_data = parser.readBytes(sh.misc_data_size)
    sh.output_misc_data = parser.readBytes(sh.misc_data_size)

    sh.format_info = parser.readBytes(0x40)

    sh.stream_name = parser.readCString()

    # Total chunk size = 12-byte header + payload
    # Padding = (12 + payload_size) - current_position
    total_chunk_size = 12 + sh.header.size
    _pad2 = total_chunk_size - parser.tell()
    if _pad2 > 0:
        parser.skip(_pad2)

    return sh


def _2057_read_stream_chunk_data(parser: Parser) -> AudioStream_2057_StreamData:
    sd = AudioStream_2057_StreamData()

    sd.header = RWHeader.read(parser)

    expect_chunk_type_or_raise(
        sd.header,
        CHUNK_RWSSTREAM_2057_STREAM_DATA,
        "Not a 2057 RWS (STREAM_DATA)",
    )

    sd.data = parser.readBytes(sd.header.size)

    return sd


def _2057_read_stream_chunk(parser: Parser) -> AudioStream_2057_Stream:
    stream = AudioStream_2057_Stream()

    stream.header = RWHeader.read(parser)

    expect_chunk_type_or_raise(
        stream.header, CHUNK_RWSSTREAM_2057_STREAM, "Not a 2057 RWS (STREAM)"
    )

    buf = Parser(parser.readBytes(stream.header.size), endian="little")

    stream.header_info = _2057_read_stream_chunk_header(buf)
    stream.stream_data = _2057_read_stream_chunk_data(buf)

    return stream


def _write_2057(rws: AudioStream_2057, filepath: Union[str, Path]):
    stamp = rws.header.library_id_stamp

    buf = io.BytesIO()

    _write_bytes(buf, rws._unk1)
    padding = max(0, 0x34 - len(rws._unk1))
    buf.write(b"\x00" * padding)

    if len(rws.name) > 32:
        raise ValueError("Name too long to fit in header (max 32 bytes)")
    _write_fixed_string(buf, rws.name, len(rws.name) + 1)

    remaining_length = 32 - len(rws.name) - 1
    buf.write(b"\x00" * remaining_length)

    inner = io.BytesIO()
    _write_header(inner, CHUNK_RWSSTREAM_2057_FILE_HEADER, len(buf.getvalue()), stamp)
    inner.write(buf.getvalue())

    rws.file_data.write(inner, stamp)

    rws_header = RWHeader(CHUNK_RWSSTREAM_2057, len(inner.getvalue()), stamp).pack()
    with open(filepath, "wb") as f:
        f.write(rws_header)
        f.write(inner.getvalue())


def load_2057(filepath: Union[str, Path]) -> AudioStream_2057:
    """Load a RWS file from disk with the 2057 structure

    Args:
        filepath: Path to the .rws file.

    Returns:
        Parsed AudioStream_2057.
    """
    rws = AudioStream_2057()

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

        rws.header = RWHeader.read(parser)

        expect_chunk_type_or_raise(
            rws.header, CHUNK_RWSSTREAM_2057, "Not a 2057 RWS (TOP)"
        )

        rws.file_header = RWHeader.read(parser)

        expect_chunk_type_or_raise(
            rws.file_header,
            CHUNK_RWSSTREAM_2057_FILE_HEADER,
            "Not a 2057 RWS (FILE_HEADER)",
        )

        rws._unk1 = parser.readBytes(0x34)
        rws.name = parser.readCString()
        rws._unk2 = parser.readBytes(rws.file_header.size - 0x34 - len(rws.name) - 1)

        rws.file_data = AudioStream_2057_Data()
        rws.file_data.data_header = RWHeader.read(parser)
        rws.file_data.total_subsongs = parser.readUint32()

        streams = []
        for i in range(rws.file_data.total_subsongs):
            try:
                streams.append(_2057_read_stream_chunk(parser))
            except Exception as e:
                print(f"Error reading stream {i}: {e}")
                raise e

        rws.file_data.subsongs = streams

    return rws
