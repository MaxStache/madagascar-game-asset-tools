from parser import Parser
from enum import Enum
import tkinter as tk
from tkinter import ttk
import wave
import ima_adpcm


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


def read_rws_string(parser: Parser):
    """Null-terminated string padded to next 0x10 boundary (padding is garbage)."""
    s = parser.readCString()
    null_pos = len(s)
    padded_size = null_pos + (0x10 - (null_pos % 0x10))
    padding_remaining = padded_size - null_pos - 1  # chars + null already consumed
    if padding_remaining > 0:
        parser.skip(padding_remaining)
    return s


def read_base_header(parser: Parser):
    # 0x00: actual header size (less than chunk size)
    # 0x04/08/10: sizes of various sections
    # 0x14/18: config?  0x1C: null?
    _unk = parser.readBytes(0x20)
    total_segments = parser.readUint32()  # 0x20
    _unk2 = parser.readUint32()  # 0x24: config?
    total_layers = parser.readUint32()  # 0x28
    # 0x2C: config?  0x30: 0x800?  0x34: block_layers_size?  0x38: data offset  0x3C: 0?
    _unk3 = parser.readBytes(0x14)  # 0x2C-0x3F
    file_uuid = parser.readBytes(0x10)  # 0x40-0x4F
    return {
        "total_segments": total_segments,
        "total_layers": total_layers,
        "file_uuid": file_uuid,
    }


def read_segment_info(parser: Parser):
    # 0x00/04/0C: config?
    _unk = parser.readBytes(0x18)
    layers_size = parser.readUint32()  # 0x18: sum of all layer sizes incl. padding
    segment_offset = parser.readUint32()  # 0x1C: byte offset into the data chunk
    return {
        "layers_size": layers_size,
        "segment_offset": segment_offset,
    }


def read_layer_info(parser: Parser):
    _unk1 = parser.readUint32()  # 0x00
    _unk2 = parser.readUint32()  # 0x04
    _unk3 = parser.readUint32()  # 0x08: null?
    _samples_per_frame = parser.readUint32()  # 0x0C
    block_size_padded = parser.readUint32()  # 0x10: block size with inter-layer padding
    _unk4 = parser.readUint32()  # 0x14
    interleave = parser.readUint16()  # 0x18
    frame_size = parser.readUint16()  # 0x1A
    _unk5 = parser.readUint32()  # 0x1C: codec related?
    block_size = parser.readUint32()  # 0x20: block size without padding
    layer_start = parser.readUint32()  # 0x24: skip-data offset within segment
    return {
        "block_size_padded": block_size_padded,
        "interleave": interleave,
        "frame_size": frame_size,
        "block_size": block_size,
        "layer_start": layer_start,
    }


def read_layer_config(parser: Parser):
    sample_rate = parser.readUint32()  # 0x00
    _unk1 = parser.readUint32()  # 0x04
    _layer_size = parser.readUint32()  # 0x08: same or close to usable size
    bit_depth = parser.readUint8()  # 0x0C: bits per sample
    channels = parser.readUint8()  # 0x0D
    _unk2 = parser.readBytes(0x0E)  # 0x0E-0x1B
    codec_uuid = read_codec_uuid(parser)  # 0x1C: first 4 bytes of GUID
    codec_uuid_rest = parser.readBytes(12)  # 0x20-0x2B: remaining 12 bytes

    dsp_data = None
    if codec_uuid == CodecUUID.DSPADPCM:
        # Extra 0x60-byte block present for DSP-ADPCM layers (GCN/Wii, big-endian)
        _dsp_unk1 = parser.readBytes(0x1C)  # +0x00: approx num samples / loop related
        coefs = parser.readBytes(0x20)  # +0x1C: 16 x s16 coefs (big-endian)
        _dsp_unk2 = parser.readBytes(0x04)  # +0x3C
        hist = parser.readBytes(0x04)  # +0x40: hist1 + hist2 (big-endian s16)
        _dsp_unk3 = parser.readBytes(0x1C)  # +0x44
        dsp_data = {"coefs": coefs, "hist": hist}

    _pad = parser.readBytes(0x04)  # padding/garbage after every layer config

    return {
        "sample_rate": sample_rate,
        "bit_depth": bit_depth,
        "channels": channels,
        "codec_uuid": codec_uuid,
        "codec_uuid_rest": codec_uuid_rest,
        "dsp_data": dsp_data,
    }


def read_header_chunk(parser: Parser):
    rw_header = parser.readRWChunkHeader()  # id = 0x80E
    buf = Parser(parser.readBytes(rw_header["size"]), endian="little")
    # NOTE: GCN/Wii/X360 builds are big-endian; pass endian="big" if needed.

    base = read_base_header(buf)
    total_segments = base["total_segments"]
    total_layers = base["total_layers"]

    file_name = read_rws_string(buf)

    segments = [read_segment_info(buf) for _ in range(total_segments)]

    # Usable (non-padded) size per subsong.
    # Order: seg1/layer1 ... seg1/layerN, seg2/layer1 ... segM/layerN
    usable_sizes = [buf.readUint32() for _ in range(total_segments * total_layers)]

    segment_uuids = [buf.readBytes(0x10) for _ in range(total_segments)]
    segment_names = [read_rws_string(buf) for _ in range(total_segments)]

    layer_infos = [read_layer_info(buf) for _ in range(total_layers)]
    layer_configs = [read_layer_config(buf) for _ in range(total_layers)]

    layer_uuids = [buf.readBytes(0x10) for _ in range(total_layers)]
    layer_names = [read_rws_string(buf) for _ in range(total_layers)]

    # Remainder of buf is garbage padding (uninitialized memory, may contain stray strings)

    return {
        "rw_header": rw_header,
        "file_name": file_name,
        "total_segments": total_segments,
        "total_layers": total_layers,
        "file_uuid": base["file_uuid"],
        "segments": segments,
        "usable_sizes": usable_sizes,
        "segment_uuids": segment_uuids,
        "segment_names": segment_names,
        "layer_infos": layer_infos,
        "layer_configs": layer_configs,
        "layer_uuids": layer_uuids,
        "layer_names": layer_names,
    }


def read_data_chunk(parser: Parser):
    rw_header = parser.readRWChunkHeader()  # id = 0x80F
    data = parser.readBytes(rw_header["size"])
    return {
        "rw_header": rw_header,
        "data": data,
    }


def read_rws_80d(data: bytes):
    parser = Parser(data, endian="little")

    chunk_header = parser.readRWChunkHeader()  # File chunk (0x80D)
    file_header = read_header_chunk(parser)  # Header chunk (0x80E)
    file_data = read_data_chunk(parser)  # Data chunk (0x80F)

    return {
        "header": chunk_header,
        "file_header": file_header,
        "file_data": file_data,
    }


def write_stream_to_file(file, seg_idx, filename, layer_idx=0):
    fh = file["file_header"]
    config = fh["layer_configs"][layer_idx]
    info = fh["layer_infos"][layer_idx]
    seg = fh["segments"][seg_idx]

    codec = config["codec_uuid"]
    name = fh["segment_names"][seg_idx]

    print(
        f"Stream '{name}' - Codec: {codec}, Sample Rate: {config['sample_rate']}, Bit Depth: {config['bit_depth']}, Channels: {config['channels']}"
    )

    raw   = file["file_data"]["data"]
    start = seg["segment_offset"] + info["layer_start"]
    total = fh["usable_sizes"][seg_idx * fh["total_layers"] + layer_idx]

    # Audio is split into super-blocks of block_size bytes, each padded to
    # block_size_padded. Collect only the audio portion of each super-block.
    chunks = []
    pos, remaining = start, total
    while remaining > 0:
        n = min(info["block_size"], remaining)
        chunks.append(raw[pos : pos + n])
        pos += info["block_size_padded"]
        remaining -= n
    data = b"".join(chunks)

    if codec == CodecUUID.PCM16:
        pcm = data
        sampwidth = config["bit_depth"] // 8
    elif codec in (CodecUUID.IMAADPCM, CodecUUID.XBOXIMA):
        pcm = ima_adpcm.decode(data, config["channels"], info["frame_size"])
        num_samples = ima_adpcm.bytes_to_samples(len(data), config["channels"])
        pcm = pcm[:num_samples * 2]
        sampwidth = 2
    else:
        raise NotImplementedError(f"Codec {codec} not supported for writing")

    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(config["channels"])
        wav_file.setsampwidth(sampwidth)
        wav_file.setframerate(config["sample_rate"])
        wav_file.writeframes(pcm)


if __name__ == "__main__":
    with open("banquetAudioStreamMU.rws", "rb") as f:
        data = f.read()

    file = read_rws_80d(data)
    header = file["file_header"]

    total_segments = header["total_segments"]
    total_layers = header["total_layers"]
    print(
        f"File: {header['file_name']!r}  segments={total_segments}  layers={total_layers}"
    )

    fh = file["file_header"]
    print(fh["layer_infos"][0])


    write_stream_to_file(file, seg_idx=9, filename="magickk.wav")

    root = tk.Tk()
    root.title("RWS 0x80D")

    tree = ttk.Treeview(
        root,
        columns=("Segment", "Layer", "SampleRate", "Channels", "Codec"),
        show="headings",
    )
    tree.heading("Segment", text="Segment")
    tree.heading("Layer", text="Layer")
    tree.heading("SampleRate", text="Sample Rate")
    tree.heading("Channels", text="Ch")
    tree.heading("Codec", text="Codec")

    tree.column("Segment", width=180)
    tree.column("Layer", width=150)
    tree.column("SampleRate", width=80, anchor="center")
    tree.column("Channels", width=30, anchor="center")
    tree.column("Codec", width=120)

    for seg_idx in range(total_segments):
        seg_name = header["segment_names"][seg_idx]
        for layer_idx in range(total_layers):
            layer = header["layer_configs"][layer_idx]
            layer_name = header["layer_names"][layer_idx]
            codec = layer["codec_uuid"]
            codec_str = codec.name if isinstance(codec, CodecUUID) else f"0x{codec:08X}"
            tree.insert(
                "",
                tk.END,
                values=(
                    seg_name,
                    layer_name,
                    layer["sample_rate"],
                    layer["channels"],
                    codec_str,
                ),
            )

    tree.pack(fill="both", expand=True)
    root.mainloop()
