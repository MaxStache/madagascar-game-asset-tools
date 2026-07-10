import io
from dataclasses import dataclass, field
from typing import Union

from ..lib.parser import Parser
from ..lib.writer import _write_u32
from ..rwConstants import RWSectionType
from ..rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from enum import Enum


class RW_UserDataPlugin_EntryType(Enum):
    Integer = 0x01
    Float = 0x02
    String = 0x03


@dataclass
class RW_UserDataPlugin_Entry:
    label: str = ""
    dataType: RW_UserDataPlugin_EntryType = RW_UserDataPlugin_EntryType.Integer

    numberOfObjects: int = 0
    objects: Union[list[int], list[float], list[str]] = field(default_factory=list)


@dataclass
class RW_UserDataPlugin(RW_Section):
    """https://gtamods.com/wiki/User_Data_PLG_(RW_Section)
    """
    header: RWHeader = field(default_factory=RWHeader)

    entry_count: int = 0

    entries: list[RW_UserDataPlugin_Entry] = field(default_factory=list)

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_UserDataPlugin":
        usrdataplg = RW_UserDataPlugin()
        usrdataplg.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            usrdataplg.header,
            RWSectionType.rwID_USERDATAPLUGIN.value,  # TODO: REPLACE!
            "RW_UserDataPlugin chunk type",
        )

        usrdataplg.entry_count = parser.readUint32()
        for _ in range(usrdataplg.entry_count):
            entry = RW_UserDataPlugin_Entry()
            entry.label = parser.readLengthPrefixedString()
            entry.dataType = RW_UserDataPlugin_EntryType(parser.readUint32())
            entry.numberOfObjects = parser.readUint32()

            if entry.dataType == RW_UserDataPlugin_EntryType.Integer:
                entry.objects = [parser.readInt32() for _ in range(entry.numberOfObjects)]
            elif entry.dataType == RW_UserDataPlugin_EntryType.Float:
                entry.objects = [parser.readFloat32() for _ in range(entry.numberOfObjects)]
            elif entry.dataType == RW_UserDataPlugin_EntryType.String:
                entry.objects = [parser.readLengthPrefixedString() for _ in range(entry.numberOfObjects)]
            else:
                raise ValueError(f"Unknown data type: {entry.dataType}")

            usrdataplg.entries.append(entry)

        return usrdataplg

    def write(this, f, stamp):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=RWSectionType.rwID_USERDATAPLUGIN.value,  # TODO: REPLACE!
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
