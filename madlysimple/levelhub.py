import io
import struct
from typing import cast

#from madagascar.lib.parser import Parser
from madagascar.lib.writer import write_alignedString, write_u32
from madagascar.streamfuncs import RW_sf_CreateEntity
from dataclasses import dataclass

from madagascar.streamfuncs.stringfuncs.sf_CreateEntity import (
    RW_sf_CreateEntity_Attribute,
)


@dataclass
class LevelHub(RW_sf_CreateEntity):
    @classmethod
    def from_entity(cls, entity: RW_sf_CreateEntity) -> "LevelHub":
        entity.__class__ = cls
        camd = cast(LevelHub, entity)
        return camd

    def addGlobalVariable(
        self, value: int | float, tag: int, name: str  # noqa: PYI041
    ) -> RW_sf_CreateEntity_Attribute:
        buf = io.BytesIO()

        if isinstance(value, float):
            buf.write(struct.pack("<f", value))
        else:
            buf.write(value.to_bytes(4, "little"))

        write_u32(buf, tag)
        write_alignedString(buf, name)

        return self.addAttribute("LevelHub", 1, buf.getvalue())