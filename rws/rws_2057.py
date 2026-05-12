from parser import Parser
from enum import Enum
import wave
import tkinter as tk
from tkinter import ttk


class CodecUUID(Enum):
    PCM16 = 0xD01BD217  # {D01BD217-3587-4EED-B9D9-B8E86EA9B995} PCM Signed 16-bit
    PSXADPCM = 0xD9EA9798  # {D9EA9798-BBBC-447B-96B2-654759102E16} PSX-ADPCM
    DSPADPCM = 0xF86215B0  # {F86215B0-31D5-4C29-BD37-CDBF9BD10C53} DSP-ADPCM (GCN only)


def read_codec_uuid(parser: Parser):
    value = parser.readUint32()
    return CodecUUID._value2member_map_.get(value, value)


def read_file_header_chunk(parser: Parser):
    header = parser.readRWChunkHeader()

    _unk1 = parser.skip(0x34)  # Unknown of 52 bytes
    name = parser.readCString()
    _unk2 = parser.readBytes(
        header["size"] - 0x34 - len(name) - 1
    )  # Unknown of remaining bytes after name (including null terminator)

    return {
        "header": header,
        "name": name,
    }


def read_stream_chunk_header(parser: Parser):
    rwHeader = parser.readRWChunkHeader()

    _unk1 = parser.readUint32() # Always 15
    sample_rate = parser.readUint32()
    _unk2 = parser.readUint32() # Always 4568152
    stream_size = parser.readUint32()
    bit_depth = parser.readUint8()
    channels = parser.readUint8()

    _pad1 = parser.readUint16() # Always 18

    _unk_misc_off = parser.readUint32() 
    misc_data_size = parser.readUint32()
    _unk3 = parser.readUint32() # Always 0

    codec_uuid = read_codec_uuid(parser)
    codec_uuid_rest = parser.readBytes(12)

    input_misc_data = parser.readBytes(misc_data_size)
    output_misc_data = parser.readBytes(misc_data_size)

    format_info = parser.readBytes(0x40)

    stream_name = parser.readCString()

    # Total chunk size = 12-byte header + payload
    # Padding = (12 + payload_size) - current_position
    total_chunk_size = 12 + rwHeader["size"]
    _pad2 = total_chunk_size - parser.tell()
    if _pad2 > 0:
        parser.skip(_pad2)

    return {
        "rwHeader": rwHeader,
        "sample_rate": sample_rate,
        "stream_size": stream_size,
        "bit_depth": bit_depth,
        "channels": channels,
        "codec_uuid": codec_uuid,
        "codec_uuid_rest": codec_uuid_rest,
        "input_misc_data": input_misc_data,
        "output_misc_data": output_misc_data,
        "format_info": format_info,
        "stream_name": stream_name,
    }


def read_stream_chunk_data(parser: Parser, header_info):
    header = parser.readRWChunkHeader()
    data = parser.readBytes(header["size"])
    return {
        "header": header,
        "data": data,
    }


def read_stream_chunk(parser: Parser):
    header = parser.readRWChunkHeader()

    buf = Parser(parser.readBytes(header["size"]), endian="little")

    header_info = read_stream_chunk_header(buf)
    stream_data = read_stream_chunk_data(buf, header_info)

    return {
        "header": header,
        "stream_header": header_info,
        "stream_data": stream_data,
    }


def read_file_data_chunk(parser: Parser):
    header = parser.readRWChunkHeader()

    total_subsongs = parser.readUint32()

    streams = []
    for i in range(total_subsongs):
        try:
            streams.append(read_stream_chunk(parser))
        except EOFError:
            print(
                "Warning: Reached end of file while reading stream chunks at index: ", i
            )
            break

    return {
        "header": header,
        "total_subsongs": total_subsongs,
        "streams": streams,
    }


def read_rwa_RWS(data):
    parser = Parser(data, endian="little")

    chunk_header = parser.readRWChunkHeader()

    file_header = read_file_header_chunk(parser)

    file_data = read_file_data_chunk(parser)

    return {
        "header": chunk_header,
        "file_header": file_header,
        "file_data": file_data,
    }


def write_stream_to_file(stream, filename):
    header = stream["stream_header"]
    data = stream["stream_data"]["data"]

    codec = header["codec_uuid"]

    print(
        f"Stream '{header['stream_name']}' - Codec: {codec}, Sample Rate: {header['sample_rate']}, Bit Depth: {header['bit_depth']}, Channels: {header['channels']}"
    )

    if codec != CodecUUID.PCM16:
        raise NotImplementedError(f"Codec {codec} not supported for writing")

    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(header["channels"])
        wav_file.setsampwidth(header["bit_depth"] // 8)
        wav_file.setframerate(header["sample_rate"])
        wav_file.writeframes(data)


if __name__ == "__main__":
    with open("Levels/banquet/.rws", "rb") as f:
        data = f.read()

    file = read_rwa_RWS(data)

    print("SUBSTREAMS:", len(file["file_data"]["streams"]))
    #stream = file["file_data"]["streams"][0]

    # write_stream_to_file(stream, "output.wav")

 