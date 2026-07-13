import io
import uuid
from dataclasses import dataclass, field

from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import (
    RW_Section,
    RWHeader,
    expect_chunk_type_or_raise,
    _write_u32,
    _write_bytes,
)
from formats.sections.RWA.WAVESTRUCT_0803 import _read_rwguid, _rwguid_bytes

# ---------------------------------------------------------------------------
# rwaID_WAVEDICT_DICT (0x80A) -- the wave dictionary's own struct chunk.
#
# Reverse-engineered from Game.exe (Madagascar):
#   RtWaveDict_ReadBody       @ 0x0050d3d0  (reads the 0x80A body raw, then:)
#   RtWaveDict_InitFromStruct @ 0x0050d750  (interprets it -> FUN_0050d750)
#
# This is the raw memory image of an RtWaveDictionary object, written verbatim.
# The only persisted information is `info`, `guid` and `name`; everything else is
# a presence flag, an ownership word, or an intrusive linked-list pointer whose
# on-disk value is a stale address the loader immediately recomputes. We read
# every field so we can round-trip exactly, but a freshly-built dict only needs
# to set info / guid / name (the writer synthesizes valid presence flags).
#
# Object layout (0x34 byte base, then name):
#   +0x00  void*   guid_ptr      presence flag for the GUID (loader: if !=0 -> use guid@+0x24)
#   +0x04  void*   name_ptr      presence flag for the name (loader: if !=0 -> use name@+0x34)
#   +0x08  u32     ownership     bit0 = owns guid mem, bit1 = owns name mem (0 = embedded)
#   +0x0C  void*   entries.next  head of the dict's wave-entry linked list (reset to self)
#   +0x10  void*   entries.prev  other end of that list head (reset to self)
#   +0x14  u32     entries.end   list terminator / count (reset to 0)
#   +0x18  u8[4]   info          byte +0x1B bit3 => big-endian sample data
#   +0x1C  void*   registry.next links dict into the global dictionary list (recomputed)
#   +0x20  void*   registry.prev prev link of that global-list node (recomputed)
#   +0x24  RWGUID  guid          dictionary identity GUID
#   +0x34  char[]  name          null-terminated dictionary name
#   ...    trailing padding / leftover buffer bytes
#
# NOTE: RenderWare GUIDs store Data1/2/3 little-endian on disk (uuid bytes_le).
# ---------------------------------------------------------------------------

_BASE_SIZE = 0x34  # bytes before the name

# The loader only tests these pointer fields for != 0 (then recomputes them),
# so any nonzero value marks "present". Used when serializing a fresh dict.
_PRESENT = 0xFFFFFFFF


@dataclass
class RW_WaveDict_Dict(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    # -- serialized RtWaveDictionary object fields (runtime pointers on disk) --
    _guid_ptr: int = 0        # +0x00  presence flag for guid  (runtime -> &guid)
    _name_ptr: int = 0        # +0x04  presence flag for name  (runtime -> &name)
    _ownership: int = 0       # +0x08  owns-guid (bit0) / owns-name (bit1) flags
    _entries_next: int = 0    # +0x0C  wave-entry list head .next (reset to self on load)
    _entries_prev: int = 0    # +0x10  wave-entry list head .prev (reset to self on load)
    _entries_end: int = 0     # +0x14  list terminator / count   (reset to 0 on load)
    info: bytes = b"\x00\x00\x00\x00"  # +0x18  info word (endianness flag in byte +0x1B bit3)
    _registry_next: int = 0   # +0x1C  global dict-registry link .next (recomputed on load)
    _registry_prev: int = 0   # +0x20  global dict-registry link .prev (recomputed on load)

    # -- persisted data --
    guid: uuid.UUID = None    # +0x24  dictionary GUID
    name: str = ""            # +0x34  null-terminated dictionary name

    _trailing: bytes = b""    # leftover bytes after the name (padding / buffer garbage)

    @property
    def has_guid(self) -> bool:
        return self._guid_ptr != 0

    @property
    def has_name(self) -> bool:
        return self._name_ptr != 0

    @property
    def is_big_endian(self) -> bool:
        """True when the dictionary's sample data is stored big-endian (GCN/Wii)."""
        return bool(self.info[3] & 0x08)

    @staticmethod
    def read(orig_parser: Parser, parent=None) -> "RW_WaveDict_Dict":
        dict_struct = RW_WaveDict_Dict()
        dict_struct.header = RWHeader.read(orig_parser)
        expect_chunk_type_or_raise(
            dict_struct.header,
            RWSectionType.rwaID_WAVEDICT_DICT.value,
            "RW_WaveDict_Dict chunk type",
        )

        parser = Parser(orig_parser.read(dict_struct.header.size), endian="little")

        dict_struct._guid_ptr = parser.readUint32()
        dict_struct._name_ptr = parser.readUint32()
        dict_struct._ownership = parser.readUint32()
        dict_struct._entries_next = parser.readUint32()
        dict_struct._entries_prev = parser.readUint32()
        dict_struct._entries_end = parser.readUint32()
        dict_struct.info = parser.readBytes(4)
        dict_struct._registry_next = parser.readUint32()
        dict_struct._registry_prev = parser.readUint32()
        dict_struct.guid = _read_rwguid(parser)
        dict_struct.name = parser.readCString()
        dict_struct._trailing = parser.readRemaining()

        return dict_struct

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        # Synthesize valid presence flags for freshly-built dicts (the loader only
        # checks for nonzero); preserve the original pointer values on round-trip.
        guid_ptr = this._guid_ptr or (_PRESENT if this.guid is not None else 0)
        name_ptr = this._name_ptr or (_PRESENT if this.name else 0)

        _write_u32(buf, guid_ptr)
        _write_u32(buf, name_ptr)
        _write_u32(buf, this._ownership)
        _write_u32(buf, this._entries_next)
        _write_u32(buf, this._entries_prev)
        _write_u32(buf, this._entries_end)
        _write_bytes(buf, this.info)
        _write_u32(buf, this._registry_next)
        _write_u32(buf, this._registry_prev)
        _write_bytes(buf, _rwguid_bytes(this.guid) if this.guid is not None else b"\x00" * 16)
        _write_bytes(buf, this.name.encode("latin-1") + b"\x00")
        _write_bytes(buf, this._trailing)

        payload = buf.getvalue()
        rw_header = RWHeader(
            type=RWSectionType.rwaID_WAVEDICT_DICT.value,
            size=len(payload),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(payload)

    def __repr__(self):
        return (
            f"RW_WaveDict_Dict(name={self.name!r}, guid=\"{self.guid}\", "
            f"info=0x{self.info.hex().upper()}, big_endian={self.is_big_endian})"
        )
