import io
import struct
from typing import cast

# from madagascar.lib.parser import Parser
from madagascar.lib.writer import write_alignedString, write_u32
from madagascar.lib.parser import Parser
from madagascar.streamfuncs import RW_sf_CreateEntity
from dataclasses import dataclass

from madagascar.streamfuncs.stringfuncs.sf_CreateEntity import (
    RW_sf_CreateEntity_Attribute,
)

LEVEL_HUB_CLASSNAME = "LevelHub"


@dataclass
class LevelHub(RW_sf_CreateEntity):
    @classmethod
    def from_entity(cls, entity: RW_sf_CreateEntity) -> "LevelHub":
        entity.__class__ = cls
        camd = cast(LevelHub, entity)
        return camd

    def getGlobalVariableAttributes(self) -> list[RW_sf_CreateEntity_Attribute]:
        return self.getAttributes("LevelHub", 1)

    def getGlobalVariables(self) -> list[tuple[int | float, int, str]]:
        """Return the global variables stored in the LevelHub.

        Tuple format:
            - value (int | float)
            - tag (int)
            - name (str)
        """
        variables: list[tuple[int | float, int, str]] = []

        for attr in self.getAttributes(LEVEL_HUB_CLASSNAME, 1):
            parser = Parser(attr.data)

            parser.skip(4)
            tag = parser.readUint32()
            parser.offset -= 8

            # print("0x" + tag.to_bytes(1, "little").hex())

            if tag == 0x02:  # reference
                value = parser.readUint32()
            elif (tag & 0xF0) in (0x10, 0x80):
                value = parser.readFloat()
            elif (tag & 0xF0) == 0x00:
                value = parser.readUint32()
            else:
                raise ValueError(f"Unsupported LevelHub variable tag: 0x{tag:08X}")

            parser.skip(4)
            name = parser.readPaddedCString()

            variables.append((value, tag, name))

        return variables

    def addGlobalVariableSoft(
        self,
        value: int | float,  # noqa: PYI041
        tag: int,
        name: str,
    ) -> RW_sf_CreateEntity_Attribute | None:
        """Adds a new variable entry or returns None if there is already an entry with the same name"""
        buf = io.BytesIO()

        for var in self.getGlobalVariables():
            if var[2] == name:
                return None

        if isinstance(value, float):
            buf.write(struct.pack("<f", value))
        else:
            buf.write(value.to_bytes(4, "little"))

        write_u32(buf, tag)
        write_alignedString(buf, name)

        return self.addAttribute(LEVEL_HUB_CLASSNAME, 1, buf.getvalue())

    def addGlobalVariable(
        self,
        value: int | float,  # noqa: PYI041
        tag: int,
        name: str,
    ) -> RW_sf_CreateEntity_Attribute:
        """Adds a new variable entry or raises if there is already an entry with the same name"""
        var = self.addGlobalVariableSoft(value, tag, name)
        if var is None:
            raise ValueError(
                "Error while adding a variable to LevelHub entity, there already is a variable with the same name"
            )

        return var

    def setGlobalVariableSoft(
        self,
        value: int | float,  # noqa: PYI041
        tag: int,
        name: str,
    ) -> RW_sf_CreateEntity_Attribute | None:
        """Sets an existing variable or returns None if it does not exist."""
        for attr, var in zip(
            self.getGlobalVariableAttributes(),
            self.getGlobalVariables(),
            strict=True,
        ):
            if var[2] != name:
                continue
    
            buf = io.BytesIO()
    
            if isinstance(value, float):
                buf.write(struct.pack("<f", value))
            else:
                buf.write(value.to_bytes(4, "little"))
    
            write_u32(buf, tag)
            write_alignedString(buf, name)
    
            attr.data = buf.getvalue()
            return attr
    
        return None


    def setGlobalVariable(
        self,
        value: int | float,  # noqa: PYI041
        tag: int,
        name: str,
    ) -> RW_sf_CreateEntity_Attribute:
        """Sets an existing variable or raises if it does not exist."""
        var = self.setGlobalVariableSoft(value, tag, name)

        if var is None:
            raise ValueError(
                f"Error while setting LevelHub variable, variable {name!r} does not exist"
            )

        return var

    def setOrCreateGlobalVariable(
        self,
        value: int | float,  # noqa: PYI041
        tag: int,
        name: str,
    ) -> RW_sf_CreateEntity_Attribute:
        """Sets an existing variable or creates it if it does not exist."""
        var = self.setGlobalVariableSoft(value, tag, name)
    
        if var is not None:
            return var
    
        return self.addGlobalVariable(value, tag, name)