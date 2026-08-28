from madagascar.stream import load_stream
from madlysimple import CProtoActor

street = load_stream("Levels/street.stream")
kony = load_stream("Levels/kingofny.stream")

kony.write_log("kony.gig.txt")

# ADD MARTY SCRIPT TO LEVEL
street.append(kony.assetByName("Marty_RunAsPlayer.AI").duplicate())

# ADD MARTY MODEL TO LEVEL
street.append(kony.entityByName("marty_KNY_Version").duplicate())

alex_actor = CProtoActor.from_entity(street.entityByName("Alex Actor"))
alex_actor.setModelRef(
    street.entityByName(name="Gloria_SC_version")
)

street.write_log("street.gig.txt")

street.save("../../Desktop/Madagascar/Game/Levels/street.stream")