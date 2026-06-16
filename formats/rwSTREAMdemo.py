import io

from lib.parser import Parser
import rwSTREAM as rwSTREAM
from rwConstants import strfunc_func
import struct

stream = rwSTREAM.load_stream("kingofny.stream")

func = rwSTREAM.RW_strfunc_SetFrozenMode()

# stream.append(func)
# stream.replace_at_index(0, func)

rwSTREAM.write_log(stream, "kingofny_stream.txt")


def modify_int_in_stream(stream, sec_index, attr_offset, new_value):
    writeobj = bytearray(stream.contents[sec_index].data)
    buf = Parser(stream.contents[sec_index].data, endian="little")
    buf.offset = attr_offset
    buf.data  # bytes type
    print(buf.readUint32())
    struct.pack_into("<I", writeobj, attr_offset, new_value)
    buf.data = writeobj
    buf.offset = attr_offset
    print(buf.readUint32())

    stream.contents[sec_index].data = bytes(writeobj)

    rwSTREAM.write_log(stream, "banquet_stream_AFTER.txt")


def translate_matrix(matrix_bytes: bytes, dx: float, dy: float, dz: float) -> bytes:
    """
    Translate a 4x4 float32 matrix.
    Translation is assumed to be in row 4, columns 1-3.
    """

    if len(matrix_bytes) != 64:
        raise ValueError("Expected 64 bytes (16 float32s)")

    m = list(struct.unpack("<16f", matrix_bytes))

    # row 4: indices 12, 13, 14
    m[12] += dx
    m[13] += dy
    m[14] += dz

    return struct.pack("<16f", *m)


for e in stream.contents:
    chunk_type = rwSTREAM._getStrfuncFromChunkType(e.header.type)
    if chunk_type == strfunc_func.sf_CreateEntity:
        parser = Parser(e.data, endian="little")
        create_call = rwSTREAM.RW_strfunc_CreateEntity.read(parser)

        class_thing = create_call.find_first_class_with_command("CAttributeHandler", 0)
        if class_thing is not None:
            # pitch_attrib = class_thing.find_first_attribute(7)

            # pitch_attrib_value = struct.pack("<I", 1)
            # pitch_attrib.data = pitch_attrib_value

            # class_thing.find_first_attribute(1).data = translate_matrix(
            #    class_thing.find_first_attribute(1).data,
            #    0,
            #    0,
            #    0
            # )
            class_thing.find_first_attribute(0).data = struct.pack("<I", 1)

        #lvlhub = create_call.find_first_class("LevelHub")
        #if lvlhub is not None:
        #    for attr in  lvlhub.find_all_attributes(1):
        #        if b"\x64\x65\x61\x74\x68\x2c\x20\x73\x65\x74\x20\x74\x68\x69\x73\x20\x74" in attr.data:
        #            attr.data = b"\x00\x00\x00\x00\x00\x00\x00\x01\x5f\x66\x6f\x72\x20\x6e\x6f\x20\x64\x65\x61\x74\x68\x2c\x20\x73\x65\x74\x20\x74\x68\x69\x73\x20\x74\x6f\x20\x31\x00\xbf\xbf\xbf"

        buf = io.BytesIO()
        create_call.write(buf)
        e.data = buf.getvalue()

rwSTREAM.write_log(stream, "kingofny_stream_new.txt")
stream.save("../../Desktop/Madagascar/Game/Levels/kingofny.stream")


gs = rwSTREAM.load_stream("global.stream")

for e in gs.contents:
    chunk_type = rwSTREAM._getStrfuncFromChunkType(e.header.type)
    if chunk_type == strfunc_func.sf_CreateEntity:
        parser = Parser(e.data, endian="little")
        buf = io.BytesIO(e.data)

        create_call = rwSTREAM.RW_strfunc_CreateEntity.read(parser)

        class_thing = create_call.find_first_class("CDebugTools")
        if class_thing is not None:
            class_thing.find_first_attribute(0).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(1).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(2).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(3).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(4).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(5).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(6).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(7).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(8).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(9).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(10).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(11).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(12).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(13).data = struct.pack("<I", 1)
            class_thing.find_first_attribute(16).data = struct.pack("<I", 0)

        create_call.write(buf)

        e.data = buf.getvalue()


rwSTREAM.write_log(gs, "global_stream.txt")

gs.save("../../Desktop/Madagascar/Game/Levels/global.stream")
