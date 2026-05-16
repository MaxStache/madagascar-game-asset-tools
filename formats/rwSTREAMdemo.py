from lib.parser import Parser
import rwSTREAM as rwSTREAM
import struct

stream = rwSTREAM.load_stream("banquet.stream")

func = rwSTREAM.RW_strfunc_SetFrozenMode()

#stream.append(func)
#stream.replace_at_index(0, func)

rwSTREAM.write_log(stream, "banquet_stream.txt")


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


#modify_int_in_stream(stream, 1804, 0x134, 1)
#modify_int_in_stream(stream, 1804, 0x14c, 1)
#modify_int_in_stream(stream, 1804, 0x158, 1)
#modify_int_in_stream(stream, 1804, 0x170, 1)
#modify_int_in_stream(stream, 1804, 0x194, 1)
#modify_int_in_stream(stream, 1804, 0x1a0, 1)

modify_int_in_stream(stream, 1765, 0xd8, 0)

#stream_global = rwSTREAM.load_stream("global.stream")
#rwSTREAM.write_log(stream_global, "global_stream.txt")

stream.save("C:/Users/Max/Desktop/Madagascar_ENG/Game/Levels/banquet.stream")