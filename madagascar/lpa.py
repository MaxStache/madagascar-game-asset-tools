import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Self, cast, override
from madagascar.lib.parser import Parser
from madagascar.lib.writer import (
    write_f32,
    write_lengthPrefixedString,
    write_s32,
    write_u8,
    write_u32,
)
from enum import IntEnum


class TFB_KeyType(IntEnum):
    BOOL = 0  # 1 byte, no interpolation
    BYTE = 1  # 1 byte, no interpolation
    INT = 2  # 4 byte i32, interpolated then truncated
    FLOAT = 3  # 4 byte f32, interpolated linearly
    COLOR = 4  # 4x 4 byte f32, interpolated linearly


@dataclass
class RW_TFB_KFSet_Key:
    time: float = field(default=0.0)
    key_type: TFB_KeyType = field(default=TFB_KeyType.BOOL)

    value: bool | int | float | list[float] | None = field(default=None)

    @classmethod
    def read(cls, parser: Parser) -> "RW_TFB_KFSet_Key":
        time = parser.readFloat()
        key_type = TFB_KeyType(parser.readUint32())

        value = None
        if key_type == TFB_KeyType.BOOL:  # noqa: SIM114
            value = bool(parser.readBytes(1))
        elif key_type == TFB_KeyType.BYTE:
            value = bool(parser.readBytes(1))
        elif key_type == TFB_KeyType.INT:
            value = parser.readInt32()
        elif key_type == TFB_KeyType.FLOAT:
            value = parser.readFloat()
        elif key_type == TFB_KeyType.COLOR:
            value = [
                parser.readFloat(),
                parser.readFloat(),
                parser.readFloat(),
                parser.readFloat(),
            ]
        else:
            value = None

        return cls(time, key_type, value)

    def write(self, f: BinaryIO):
        write_f32(f, self.time)
        write_u32(f, int(self.key_type))

        if self.key_type == TFB_KeyType.BOOL:
            write_u8(f, int(bool(self.value)))
        elif self.key_type == TFB_KeyType.BYTE:
            write_u8(f, int(cast(int, self.value)) & 0xFF)
        elif self.key_type == TFB_KeyType.INT:
            write_s32(f, int(cast(int, self.value)))
        elif self.key_type == TFB_KeyType.FLOAT:
            write_f32(f, float(cast(float, self.value)))
        elif self.key_type == TFB_KeyType.COLOR:
            for component in cast(list[float], self.value):
                write_f32(f, component)


@dataclass
class RW_TFB_KFSet:
    version: int = field(default=0x0F0F0002)
    name: str = field(default="")

    value_type: TFB_KeyType = field(default=TFB_KeyType.BOOL)  # only informational

    keys: list[RW_TFB_KFSet_Key] = field(default_factory=list)

    duration: float = field(default=0)  # v2 only

    @classmethod
    def read(cls, parser: Parser) -> "RW_TFB_KFSet":
        version = parser.readUint32()
        if version == 0x0F0F0001:
            raise NotImplementedError("RW_TFB_KFSet version 1 not implemented")

        parser.skip(4)  # Never read by any game code. 0 in every shipped file.
        name = parser.readLengthPrefixedString()
        parser.skip(4)  # Never read by any game code. 0 in every shipped file.

        value_type = TFB_KeyType(parser.readUint32())

        key_count = parser.readUint32()

        keys: list[RW_TFB_KFSet_Key] = []
        for _ in range(key_count):
            keys.append(RW_TFB_KFSet_Key.read(parser))

        duration = parser.readFloat()

        return cls(
            version=version,
            name=name,
            value_type=value_type,
            keys=keys,
            duration=duration,
        )

    def write(self, f: BinaryIO):
        if self.version == 0x0F0F0001:
            raise NotImplementedError("RW_TFB_KFSet version 1 not implemented")

        write_u32(f, self.version)
        write_u32(f, 0)  # Never read by any game code. 0 in every shipped file.
        # Every shipped set has an empty name, stored as a bare length of 0 - so
        # only pay for the terminator when there is actually a name to terminate.
        write_lengthPrefixedString(f, self.name, addNullTerminator=bool(self.name))
        write_u32(f, 0)  # Never read by any game code. 0 in every shipped file.

        write_u32(f, int(self.value_type))
        write_u32(f, len(self.keys))

        for key in self.keys:
            key.write(f)

        write_f32(f, self.duration)


class TFB_Viseme(IntEnum):
    Rest = 0
    MBP = 1
    AA = 2
    EE = 3
    FV = 4
    OO = 5
    QUW = 6
    L = 7
    CONS = 8


@dataclass
class TFB_VisemeKey:
    time: float = field(default=0)
    viseme: TFB_Viseme = field(default=TFB_Viseme.Rest)


@dataclass
class RW_TFB_LipAnimation(RW_TFB_KFSet):
    @classmethod
    @override
    def read(cls, parser: Parser) -> Self:
        return cast(Self, super().read(parser))

    def generate_from_wav(data: bytes):
        pass

    @property
    def visemes(self) -> list[TFB_VisemeKey]:
        visemes: list[TFB_VisemeKey] = []

        for key in self.keys:
            visemes.append(TFB_VisemeKey(key.time, TFB_Viseme(key.value)))

        return visemes

    @classmethod
    def from_visemes(cls, visemes: list[TFB_VisemeKey], duration: float) -> Self:
        """Build a lip animation out of viseme keys.

        Key times are normalised (0..1 of duration), same as the `visemes`
        property returns them, so `from_visemes(anim.visemes, anim.duration)`
        round-trips a file.
        """

        if duration <= 0:
            raise ValueError("duration must be positive")

        keys = [
            RW_TFB_KFSet_Key(
                time=viseme.time,
                key_type=TFB_KeyType.INT,
                value=int(viseme.viseme),
            )
            for viseme in visemes
        ]

        return cls(value_type=TFB_KeyType.INT, keys=keys, duration=duration)


def loads_lpa(data: bytes) -> RW_TFB_LipAnimation:
    """Load a LPA from stream

    Args:
        bytestream: Bytes of the .lpa

    Returns:
        Parsed RW_TFB_LipAnimation.
    """

    parser = Parser(data, endian="little")

    return RW_TFB_LipAnimation.read(parser)


def load_lpa(filepath: str | Path) -> RW_TFB_LipAnimation:
    """Load a LPA file from disk

    Args:
        filepath: Path to the .lpa file.

    Returns:
        Parsed RW_TFB_LipAnimation
    """

    with open(filepath, "rb") as f:
        return loads_lpa(f.read())


def dumps_lpa(lipanim: RW_TFB_LipAnimation) -> bytes:
    """Serialise a LPA to bytes

    Args:
        lipanim: The lip animation to serialise.

    Returns:
        Bytes of the .lpa.
    """

    buffer = io.BytesIO()
    lipanim.write(buffer)

    return buffer.getvalue()


def save_lpa(lipanim: RW_TFB_LipAnimation, filepath: str | Path) -> None:
    """Save a LPA file to disk

    Args:
        lipanim: The lip animation to write.
        filepath: Path to the .lpa file.
    """

    with open(filepath, "wb") as f:
        lipanim.write(f)
