from madagascar.stream import load_stream

coming = load_stream("Levels/coming.stream")
banquet = load_stream("Levels/banquet.stream")

coming.entityByName("Melman Actor").tfbSetName("Alex Actor")

banquet.write_log("banquet.gig.txt")

coming.entityByName("DEFAULT").setAttribute("CameraData", 1, data=b"Alex Actor\x00\xbf")
coming.entityByName("DEFAULT").setAttribute("CameraData", 4, data=b"Alex Actor\x00\xbf")

coming.verify()
coming.save("SAVE_LOCATION")
