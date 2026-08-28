import struct
from collections.abc import Sequence
from typing import cast, overload, override

from madagascar.lib.parser import Parser
from madagascar.streamfuncs import RW_sf_CreateEntity
from dataclasses import dataclass


def _packVector3(value: Sequence[float]) -> bytes:
    values = tuple(value)
    if len(values) != 3:
        raise ValueError(f"Expected 3 offsets, got {len(values)}")
    return struct.pack("<3f", *values)


class CameraDataOffset(Sequence[float]):
    """Write-through view of a 3-float CameraData offset attribute.

    Reads like the tuple the getters used to return -- unpacking, indexing,
    iteration and comparison against a tuple all still work -- but assigning to
    an element rewrites the attribute on the entity:

        cam.lookFromOffset[1] = 12.0
        cam.lookAtOffset.heading = 90.0
    """

    __slots__ = ("_command", "_owner")

    def __init__(self, owner: "CameraData", command: int) -> None:
        self._owner = owner
        self._command = command

    def _values(self) -> tuple[float, float, float]:
        cmdp = Parser(self._owner.getAttribute("CameraData", self._command).data)
        return (cmdp.readFloat(), cmdp.readFloat(), cmdp.readFloat())

    def asTuple(self) -> tuple[float, float, float]:
        """Detached copy, for when you want a value that will not follow edits."""
        return self._values()

    @override
    def __len__(self) -> int:
        return 3

    @overload
    def __getitem__(self, index: int) -> float: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[float, ...]: ...

    @override
    def __getitem__(self, index: int | slice) -> float | tuple[float, ...]:
        return self._values()[index]

    def __setitem__(self, index: int, value: float) -> None:
        values = list(self._values())
        values[index] = float(value)  # IndexError on out of range, as with a list
        self._owner.setAttribute("CameraData", self._command, _packVector3(values))

    @property
    def horizontal(self) -> float:
        return self._values()[0]

    @horizontal.setter
    def horizontal(self, value: float) -> None:
        self[0] = value

    @property
    def vertical(self) -> float:
        return self._values()[1]

    @vertical.setter
    def vertical(self, value: float) -> None:
        self[1] = value

    @property
    def heading(self) -> float:
        return self._values()[2]

    @heading.setter
    def heading(self, value: float) -> None:
        self[2] = value

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, CameraDataOffset):
            return self._values() == other._values()
        if isinstance(other, (tuple, list)):
            values = cast(Sequence[object], other)
            return len(values) == 3 and self._values() == tuple(values)
        return NotImplemented

    @override
    def __repr__(self) -> str:
        return repr(self._values())


class CameraDataOffsetAttribute:
    """One 3-float offset command, exposed as an attribute of CameraData.

    A descriptor rather than a property because reads and writes have different
    types: reading hands back a write-through CameraDataOffset, writing accepts
    any 3-element sequence.
    """

    def __init__(self, command: int, doc: str) -> None:
        self._command = command
        self.__doc__ = doc

    @overload
    def __get__(
        self, instance: None, owner: type | None = None
    ) -> "CameraDataOffsetAttribute": ...

    @overload
    def __get__(
        self, instance: "CameraData", owner: type | None = None
    ) -> CameraDataOffset: ...

    def __get__(
        self, instance: "CameraData | None", owner: type | None = None
    ) -> "CameraDataOffset | CameraDataOffsetAttribute":
        if instance is None:
            return self
        return CameraDataOffset(instance, self._command)

    def __set__(self, instance: "CameraData", value: Sequence[float]) -> None:
        instance.setAttribute("CameraData", self._command, _packVector3(value))


@dataclass
class CameraData(RW_sf_CreateEntity):
    @classmethod
    def from_entity(cls, entity: RW_sf_CreateEntity) -> "CameraData":
        # Re-tag in place instead of copying, so writes through the properties
        # land on the very entity the stream holds.
        entity.__class__ = cls
        camd = cast(CameraData, entity)
        return camd

    def _setString(self, command: int, value: str) -> None:
        self.getAttribute("CameraData", command).setString(value)

    def _setFloat(self, command: int, value: float) -> None:
        self.setAttribute("CameraData", command, struct.pack("<f", value))

    def _setBool(self, command: int, value: bool) -> None:
        self.setAttribute("CameraData", command, struct.pack("<i", int(value)))

    @property
    def cameraDataName(self) -> str:
        return self.getAttribute("CameraData", 0).asString()

    @cameraDataName.setter
    def cameraDataName(self, value: str) -> None:
        self._setString(0, value)

    @property
    def lookFromTarget(self) -> str:
        return self.getAttribute("CameraData", 1).asString()

    @lookFromTarget.setter
    def lookFromTarget(self, value: str) -> None:
        self._setString(1, value)

    lookFromOffset = CameraDataOffsetAttribute(2, "(horizontal,vertical,heading) offsets")

    @property
    def lookFromHeadingRelative(self) -> bool:
        cmdp = Parser(self.getAttribute("CameraData", 3).data)
        return cmdp.readBool()

    @lookFromHeadingRelative.setter
    def lookFromHeadingRelative(self, value: bool) -> None:
        self._setBool(3, value)

    @property
    def lookAtTarget(self) -> str:
        return self.getAttribute("CameraData", 4).asString()

    @lookAtTarget.setter
    def lookAtTarget(self, value: str) -> None:
        self._setString(4, value)

    lookAtOffset = CameraDataOffsetAttribute(5, "(horizontal,vertical,heading) offsets")

    @property
    def lookAtHeadingRelative(self) -> bool:
        cmdp = Parser(self.getAttribute("CameraData", 6).data)
        return cmdp.readBool()

    @lookAtHeadingRelative.setter
    def lookAtHeadingRelative(self, value: bool) -> None:
        self._setBool(6, value)

    @property
    def fov(self) -> float:
        cmdp = Parser(self.getAttribute("CameraData", 7).data)
        return cmdp.readFloat()

    @fov.setter
    def fov(self, value: float) -> None:
        self._setFloat(7, value)

    @property
    def laziness(self) -> bool:
        cmdp = Parser(self.getAttribute("CameraData", 8).data)
        return cmdp.readBool()

    @laziness.setter
    def laziness(self, value: bool) -> None:
        self._setBool(8, value)
