import struct

from formats.lib.rwConstants import DEFAULT_VERSION_STAMP
from formats.lib.rw_basics import RW_Matrix4x4, Vector3, Vector4
from formats.stream import RW_StreamFile, load_stream
from formats.streamfuncs import (
    RW_sf_SetFrozenMode,
    RW_sf_SetRunningMode,
    RW_sf_EnableDirectorsCamera,
    RW_sf_SetDirectorsCameraMatrix,
)
from formats.streamfuncs.stringfuncs.sf_CreateEntity import RW_sf_CreateEntity


mystream = RW_StreamFile()

# mystream.contents.append(RW_sf_SetFrozenMode())
# mystream.contents.append(RW_sf_SetRunningMode())

sf_cammatrix = RW_sf_SetDirectorsCameraMatrix()
sf_cammatrix.matrix = RW_Matrix4x4(
    row1=Vector4(1.0, 0.0, 0.0, 0.0),  # right
    row2=Vector4(0.0, 1.0, 0.0, 0.0),  # up
    row3=Vector4(0.0, 0.0, 1.0, 0.0),  # at
    row4=Vector4(3894.0, 100.0, 6562.0, 1.0),  # pos
)
sf_cammatrix.fov = 0.74
mystream.contents.append(sf_cammatrix)
mystream.contents.append(RW_sf_EnableDirectorsCamera())
mystream.contents.append(RW_sf_SetRunningMode())

mystream.write(open("test.stream", "wb"), DEFAULT_VERSION_STAMP)

#  curl.exe --data-binary "@test.stream" http://127.0.0.1:6742/stream


def bytes_pad4_BF(data: bytes) -> bytes:
    padding = (4 - (len(data) % 4)) % 4
    return data + b"\xbf" * padding



STREAM_LIB_ID = 0x1802FFFF
kony = load_stream("kingofny.stream")

for sf in kony.contents:
    if isinstance(sf, RW_sf_CreateEntity):
        if sf.behaviour != "LevelHub":
            continue

        lvlhub = sf.find_first_class("LevelHub")
        for attr in lvlhub.find_all_attributes(1):
            if "Cheats_Enabled".encode("latin-1") in attr.data:
                attr.data = b'\x01\x00\x00\x00\x01\x00\x00\x00Cheats_Enabled?\x00'
                print("Updated atributee")
            if "Design Build".encode("latin-1") in attr.data:
                attr.data = b'\x01\x00\x00\x00\x01\x00\x00\x00Design Build?\x00'
                print("Updated atributee")

        #dircam = sf.find_first_class("GameCamera")
        #dircam.find_first_attribute(4).data = struct.pack("<I", 90)
        #string = bytes_pad4_BF(
        #    "iMsgDoRenderDirectorsCamera".encode("latin-1") + b"\x00"
        #)
        print("Updated atribute")


kony.write(open("../../Desktop/Madagascar/Game/Levels/kingofny.stream", "wb"), STREAM_LIB_ID)
