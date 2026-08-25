from typing import cast

from madagascar.streamfuncs import RW_sf_CreateEntity
from madagascar.lib.parser import Parser
from dataclasses import dataclass, field


@dataclass
class CProtoActor(RW_sf_CreateEntity):
    actorName: str = field(default="")
    waypoints: list[tuple[int,float,float,float]] = field(default_factory=list) # list of waypoints (idx, x, y, z) 

    flags: int = field(default=0)
    activationRange: float = field(default=0.0) # Distance at which the actor wakes up and starts ticking. 
    deactivationRange: float = field(default=0.0) # Distance at which it goes back to sleep.
    coneColor: int = field(default=0) # (0/3/4/8)
    blipColor: int = field(default=0) # (0/2)
    activationRangeFadePercent: int = field(default=0) # always 0

    @classmethod
    def from_entity(cls, entity: RW_sf_CreateEntity) -> "CProtoActor":
        cpa = cast(CProtoActor, entity)

        cpa.actorName = entity.getAttribute("CProtoActor", 0).asString()

        propBlockData = entity.getAttribute("CProtoActor", 1).data
        pbParser = Parser(propBlockData, endian="little")

        pbParser.skip(4)  # Version
        cpa.flags = pbParser.readUint32()
        cpa.activationRange = pbParser.readFloat()
        cpa.deactivationRange = pbParser.readFloat()
        cpa.coneColor = pbParser.readUint32()
        pbParser.skip(4) # 1 on 5727/5730. No reader found
        cpa.blipColor = pbParser.readUint32()
        cpa.activationRangeFadePercent = pbParser.readUint32()
        pbParser.skip(32) # always zero

        # TODO: FINISH THE READING OF COMMAND 1



        return cpa
