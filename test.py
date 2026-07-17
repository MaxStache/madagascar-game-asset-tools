from formats.lib.rwConstants import DEFAULT_VERSION_STAMP
from formats.stream import RW_StreamFile
from formats.streamfuncs import RW_sf_SetFrozenMode, RW_sf_SetRunningMode, RW_sf_EnableDirectorsCamera


mystream = RW_StreamFile()

#mystream.contents.append(RW_sf_SetFrozenMode())
#mystream.contents.append(RW_sf_SetRunningMode())
mystream.contents.append(RW_sf_EnableDirectorsCamera())

mystream.write(open("test.stream", "wb"), DEFAULT_VERSION_STAMP)