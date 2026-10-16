"""The three string tables at the head of every TFB script file."""

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, BinaryIO

from tfbscript.binary import write_u32, write_u8

if TYPE_CHECKING:
    from tfbscript.binary import BinaryReader


@dataclass
class StringTableEntry:
    """One entry: a length-prefixed string plus 4 bytes of metadata.

    Entry strings are `::`-separated paths such as ``myactor::actor`` or
    ``myactor::user::value`` -- the first part is the name, the last part the
    type, and the middle part (if any) the category.
    """

    string: str = field(default="")
    metadata: bytes = field(default=b"\x00\x00\x00\x00")  # 4 bytes, usually zero

    _split: list[str] = field(default_factory=list)

    def _split_myself(self) -> list[str]:
        if not self._split:
            self._split = re.split(r'(?=::(?!:))', self.string)
            self._split = [self._split[0]] + [p[2:] for p in self._split[1:]]

        
        if len(self._split) < 2:
            raise ValueError(f"String table entry '{self.string}' does not have a type part")

        if len(self._split) > 3:
            raise ValueError(f"String table entry '{self.string}' has too many parts")

        return self._split

    def __post_init__(self):
        self._split_myself()

    @classmethod
    def read(cls, reader: "BinaryReader") -> "StringTableEntry":
        length = reader.read_u8()
        string = reader.read_string(length)
        metadata = reader.read_bytes(4)

        return cls(string, metadata)

    @property
    def name(self) -> str:
        # ABC::user::value
        return self._split[0]

    @property
    def category(self) -> str | None:
        # abc::USER::value
        return self._split[-2] if len(self._split) > 2 else None

    @property
    def type(self) -> str:
        # abc::user::VALUE
        return self._split[-1]

@dataclass
class StringTable:
    """A u32 entry count followed by that many entries."""

    entries: list[StringTableEntry] = field(default_factory=list)

    @classmethod
    def read(cls, reader: "BinaryReader") -> "StringTable":
        count = reader.read_u32()
        return cls([StringTableEntry.read(reader) for _ in range(count)])

    def write(self, f: BinaryIO) -> None:
        """Write the ScriptFile to a binary file."""

        write_u32(f, len(self.entries))
        for entry in self.entries:
            write_u8(f, len(entry.string))
            f.write(entry.string.encode("latin1"))
            f.write(entry.metadata)
        
    def __len__(self) -> int:
        return len(self.entries)

    def get(self, index: int) -> StringTableEntry | None:
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return None

    def all_with_type(self, type_name: str) -> list[StringTableEntry]:
        """All entries whose type (last ``::`` part) matches, e.g. ``behavior``."""
        return [e for e in self.entries if e.type == type_name]

    def all_with_category(self, category_name: str) -> list[StringTableEntry]:
        """All entries whose category (middle ``::`` part) matches, e.g. ``user``."""
        return [e for e in self.entries if e.category == category_name]
