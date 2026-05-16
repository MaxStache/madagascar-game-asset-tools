from lib.parser import Parser
import rwSTREAM as rwSTREAM
import struct

stream = rwSTREAM.load_stream("banquet.stream")

func = rwSTREAM.RW_strfunc_SetFrozenMode()

#stream.append(func)
#stream.replace_at_index(0, func)
writeobj = bytearray(stream.contents[2658].data)
buf = Parser(stream.contents[2658].data, endian="little")
buf.offset = 0xa0
buf.data # bytes type
print(buf.readUint32())
struct.pack_into("<I", writeobj, 0xA0, 200)
buf.data = writeobj
buf.offset = 0xa0
print(buf.readUint32())

stream.contents[2658].data = bytes(buf.data)

rwSTREAM.write_log(stream, "banquet_stream.txt")

stream_global = rwSTREAM.load_stream("global.stream")
rwSTREAM.write_log(stream_global, "global_stream.txt")

stream.save("banquet_copy.stream")