import io
from dataclasses import dataclass, field
from typing import Union

from formats.lib.parser import Parser
from formats.lib.writer import _write_u32, _write_f32
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

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
    def read(parser: Parser, parent=None) -> "RW_UserDataPlugin":
        usrdataplg = RW_UserDataPlugin()
        usrdataplg.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            usrdataplg.header,
            RWSectionType.rwID_USERDATAPLUGIN.value,
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

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        _write_u32(buf, len(this.entries))

        for entry in this.entries:
            _write_u32(buf, len(entry.label))
            buf.write(entry.label.encode("latin-1", errors="replace"))
            _write_u32(buf, entry.dataType.value)
            _write_u32(buf, entry.numberOfObjects)

            if entry.dataType == RW_UserDataPlugin_EntryType.Integer:
                for obj in entry.objects:
                    _write_u32(buf, obj)
            elif entry.dataType == RW_UserDataPlugin_EntryType.Float:
                for obj in entry.objects:
                    _write_f32(buf, obj)
            elif entry.dataType == RW_UserDataPlugin_EntryType.String:
                for obj in entry.objects:
                    _write_u32(buf, len(obj))
                    buf.write(obj.encode("latin-1", errors="replace"))
            else:
                raise ValueError(f"Unknown data type: {entry.dataType}")

        rw_header = RWHeader(
            type=RWSectionType.rwID_USERDATAPLUGIN.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
