"""Madagascar (2005, PC) ``SaveGames.mem`` reader.

The file is four fixed slots, each a 0x2C header followed by a payload.  The
payload is *not* self-describing: it is a flat sequence of

    u32 id      tfb_hash("<name>::<type>")
    u32 value   bit31 set -> int (& 0x7FFFFFFF), clear -> float32

with no length, delimiter or alignment.  The game never parses it either - it
replays its live object list and asks each object how many bytes to consume,
using the stored id only as a consistency check (``FUN_004468e0`` @ 0x4468E0).

This module does the same thing: it builds a catalogue of every id that *could*
appear - from ``Levels/global.stream``'s ``LevelHub`` declarations plus the
engine's own globals - and walks the payload by looking each stored id up.  The
span of an entry is the distance to the next known id, which is what recovers
variable-length blob entries (type ``user`` with a data buffer); their length
exists nowhere on disk.

Ids come in three shapes, because ``FUN_00432af0`` formats ``"%s::%s%s"`` as
name, type name, and an optional ``"::<context type>"`` emitted when the object's
own type differs from the class token it was declared with:

    "<name>::value"           engine-created plain values
    "<name>::user"            user objects (these are the ones that carry blobs)
    "<name>::user::value"     LevelHub declarations - created through the `user`
                              factory with the `value` class token

All three were confirmed against a real save: 64/64 LevelHub names reproduce
their stored id under the third form.

Which objects end up in a save is decided by a watermark: the serializer scans
``DAT_00621F38 .. g_nWorldObjectCount``, and ``g_nWorldObjectCount`` is latched
once in ``FUN_004610b0`` right after ``LoadStreamFile("LEVELS\\GLOBAL.STREAM")``.
Everything a level declares lives above that mark and is destroyed on every
transition, so only GLOBAL.STREAM's ``LevelHub`` globals are persisted.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from formats.stream import load_stream
from formats.streamfuncs import RW_sf_CreateEntity
from typing import override
__version__ = "1.0.0"

SLOT_COUNT = 4
HEADER_SIZE = 0x2C
SAVE_VERSION = 8
CHECKSUM_SEED = 0x55555555
INT_TAG = 0x80000000

#: ``FUN_00419910`` masks the tag with 0xFFFFFF7F and switches 0..7; bit 7 means
#: the global is a *set* of that type.  Only a plain type-0 single value ends up
#: in a save, i.e. tag == 0 exactly.
TYPE_NAMES = {
    0: "value",
    1: "behavior",
    2: "actor",
    3: "message",
    4: "sound",
    5: "camera",
    6: "controller",
    7: "sprite",
}

#: Id suffix used by objects a ``LevelHub`` attribute-1 record declares: they are
#: built through the ``user`` factory carrying the ``value`` class token, so
#: ``FUN_00432af0`` emits both.
LEVELHUB_ID_TYPE = "user::value"

#: Globals the engine creates itself, above the ``DAT_00621F38`` watermark and so
#: inside the saved range, but declared nowhere in a stream file.  Listed in the
#: order a real save stores them; the walk does not depend on that order.
ENGINE_GLOBALS: tuple[tuple[str, str], ...] = (
    ("effects volume", "value"),
    ("music volume", "value"),
    ("rumble disabled", "value"),
    ("Global Placement Removed", "user"),   # the blob
    ("Next Level Auto Load", "value"),
    ("Game Running Time", "value"),
)


class SaveError(Exception):
    """Raised when a save cannot be walked against the declaration list."""


# ---------------------------------------------------------------------------
# hashing
# ---------------------------------------------------------------------------


def _fold_case(data: bytes) -> bytes:
    """Lowercase A-Z only, exactly as ``FUN_0043bb20`` does."""
    return bytes(c + 0x20 if 0x41 <= c <= 0x5A else c for c in data)


def tfb_hash(text: str | bytes) -> int:
    """CRC-32 (poly 0xEDB88320) over the case-folded string, *without* the
    final complement.  ``FUN_0043bb20`` @ 0x43BB20."""
    data = text.encode("latin-1") if isinstance(text, str) else text
    return zlib.crc32(_fold_case(data)) ^ 0xFFFFFFFF


def entry_id(name: str, type_name: str = "value") -> int:
    """Id of a save entry: ``tfb_hash("<name>::<type_name>")``.

    ``type_name`` carries the optional context component too, e.g.
    ``"user::value"`` for a LevelHub-declared global.
    """
    return tfb_hash(f"{name}::{type_name}")


# ---------------------------------------------------------------------------
# placement bitset
# ---------------------------------------------------------------------------

#: ``Global Placement Removed`` is declared with 12800 elements (``FUN_0042f370``
#: @ 0x42F370).  ``FUN_0043c2a0`` sees a boolean element type and allocates
#: ``(12800 + 0x1F) >> 5`` = 400 dwords = 1600 bytes.
GLOBAL_PLACEMENT_BITS = 12800
GLOBAL_PLACEMENT_BYTES = 1600

#: ...but only 1500 bytes reach the file: the serializer's ``n >= 0x640 ? n -= 100``
#: rule drops the last 100 bytes, so the top 800 bits are never persisted.  800 is
#: exactly the size of the per-level ``Level Placement Removed`` set
#: (``FUN_0042f3f0`` @ 0x42F3F0), which is not saved at all.
GLOBAL_PLACEMENT_SAVED_BYTES = 1500
GLOBAL_PLACEMENT_SAVED_BITS = GLOBAL_PLACEMENT_SAVED_BYTES * 8


def bit_get(blob: bytes, index: int) -> bool:
    """Read one bit, LSB-first within each byte (``FUN_0043bca0``, vtable +0x34)."""
    return bool((blob[index >> 3] >> (index & 7)) & 1)


def bit_set(blob: bytearray, index: int, value: bool = True) -> None:
    """Write one bit (``FUN_0043be20``, vtable +0x40)."""
    mask = 1 << (index & 7)
    blob[index >> 3] = (blob[index >> 3] & ~mask) | (mask if value else 0)


def set_bits(blob: bytes) -> list[int]:
    """Indices of every set bit, i.e. every placement recorded as removed."""
    return [i for i in range(len(blob) * 8) if (blob[i >> 3] >> (i & 7)) & 1]


def bit_runs(indices: list[int]) -> list[tuple[int, int]]:
    """Collapse an index list into inclusive ``(first, last)`` runs."""
    runs: list[tuple[int, int]] = []
    start = prev = None
    for i in indices:
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            runs.append((start, prev))
            start = prev = i
    if start is not None:
        runs.append((start, prev))
    return runs


def payload_checksum(payload: bytes) -> int:
    """Rot-xor checksum stored at header +0x18."""
    c = CHECKSUM_SEED
    for b in payload:
        sb = b | 0xFFFFFF00 if b >= 0x80 else b  # sign-extend the byte
        c = (c ^ sb) & 0xFFFFFFFF
        c = ((c << 1) | (c >> 31)) & 0xFFFFFFFF
    return c


# ---------------------------------------------------------------------------
# declarations (Levels/global.stream -> LevelHub attribute 1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Declaration:
    """One ``LevelHub`` attribute-1 record: ``u32 initial, u32 tag, cstring``."""

    name: str
    initial: int
    tag: int

    @property
    def is_set(self) -> bool:
        return bool(self.tag & 0x80)

    @property
    def type_index(self) -> int:
        return self.tag & 0xFFFFFF7F

    @property
    def type_name(self) -> str:
        return TYPE_NAMES.get(self.type_index, f"<bad tag 0x{self.tag:X}>")

    @property
    def is_saved(self) -> bool:
        """Only a non-set type-0 value is serialized."""
        return self.tag == 0


def read_declarations(stream_path: str | Path) -> list[Declaration]:
    """Every ``LevelHub`` attribute-1 record, in declaration order.

    Order matters: it is the order the objects are registered, which is the
    order they appear in the payload.
    """
    stream = load_stream(stream_path)
    decls: list[Declaration] = []

    for sf in stream.contents:
        if not isinstance(sf, RW_sf_CreateEntity):
            continue
        for cls in sf.classes:
            if cls.class_name != "LevelHub":
                continue
            for attr in cls.attributes:
                if attr.command != 1 or len(attr.data) < 8:
                    continue
                initial, tag = struct.unpack_from("<Ii", attr.data, 0)
                name = attr.data[8:].split(b"\x00")[0].decode("latin-1")
                decls.append(Declaration(name, initial, tag & 0xFFFFFFFF))

    return decls


def saved_declarations(stream_path: str | Path) -> list[Declaration]:
    return [d for d in read_declarations(stream_path) if d.is_saved]


def build_catalog(stream_path: str | Path) -> dict[int, str]:
    """Map every id that can appear in a payload back to its name."""
    catalog = {entry_id(n, t): n for n, t in ENGINE_GLOBALS}
    for d in saved_declarations(stream_path):
        catalog[entry_id(d.name, LEVELHUB_ID_TYPE)] = d.name
    return catalog


# ---------------------------------------------------------------------------
# save file
# ---------------------------------------------------------------------------


@dataclass
class Entry:
    id: int
    name: str | None = None
    raw: int | None = None
    blob: bytes | None = None

    @property
    def is_blob(self) -> bool:
        return self.blob is not None

    @property
    def is_int(self) -> bool:
        return self.raw is not None and bool(self.raw & INT_TAG)

    @property
    def value(self) -> int | float | bytes:
        if self.blob is not None:
            return self.blob
        assert self.raw is not None
        if self.raw & INT_TAG:
            return self.raw & 0x7FFFFFFF
        return struct.unpack("<f", struct.pack("<I", self.raw))[0]

    @override
    def __str__(self) -> str:
        label = self.name or f"<unknown 0x{self.id:08X}>"
        if self.blob is not None:
            return f"{label} = <blob {len(self.blob)} bytes>"
        return f"{label} = {self.value}"


@dataclass
class Slot:
    index: int
    payload_size_field: int
    version: int
    entry_count: int
    language_id: int
    percent_complete: int
    play_time_seconds: int
    checksum: int
    stream_name: str
    payload_ptr: int
    payload: bytes = b""
    entries: list[Entry] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """``FUN_00446670`` formats empty slots with languageId = -1."""
        return self.language_id == -1

    @property
    def checksum_ok(self) -> bool:
        return payload_checksum(self.payload) == self.checksum

    def get(self, name: str) -> int | float | bytes | None:
        for e in self.entries:
            if e.name == name:
                return e.value
        return None

    @property
    def placement_blob(self) -> bytes | None:
        """The raw ``Global Placement Removed`` bitset, 1500 bytes."""
        v = self.get("Global Placement Removed")
        return v if isinstance(v, bytes) else None

    def placements_removed(self) -> list[int]:
        """Placement ids this slot records as removed (collected/destroyed).

        The id is the placement's own ``obj+4``, loaded into the set's subscript
        register by ``FUN_0043bb70`` whenever the script's current object changes,
        so a bit index *is* a placement id.
        """
        blob = self.placement_blob
        return set_bits(blob) if blob else []

    def is_placement_removed(self, placement_id: int) -> bool:
        blob = self.placement_blob
        if blob is None or placement_id >= len(blob) * 8:
            return False
        return bit_get(blob, placement_id)


@dataclass
class SaveFile:
    slots: list[Slot] = field(default_factory=list)
    payload_size: int = 0
    catalog: dict[int, str] = field(default_factory=dict)

    def __getitem__(self, i: int) -> Slot:
        return self.slots[i]


def _split_slots(data: bytes) -> tuple[int, list[bytes]]:
    if len(data) % (4 * 4):
        raise SaveError(f"file size {len(data)} is not 4 whole dword-sized slots")
    stride = len(data) // SLOT_COUNT
    if stride <= HEADER_SIZE:
        raise SaveError(f"slot stride {stride} leaves no room for a payload")
    return stride - HEADER_SIZE, [
        data[i * stride : (i + 1) * stride] for i in range(SLOT_COUNT)
    ]


def _read_header(raw: bytes, index: int) -> Slot:
    (
        payload_size,
        version,
        entry_count,
        language_id,
        percent,
        play_time,
        checksum,
    ) = struct.unpack_from("<IIIiIiI", raw, 0)
    stream_name = raw[0x1C:0x28].split(b"\x00")[0].decode("latin-1")
    (payload_ptr,) = struct.unpack_from("<I", raw, 0x28)

    return Slot(
        index=index,
        payload_size_field=payload_size,
        version=version,
        entry_count=entry_count,
        language_id=language_id,
        percent_complete=percent,
        play_time_seconds=play_time,
        checksum=checksum,
        stream_name=stream_name,
        payload_ptr=payload_ptr,
        payload=raw[HEADER_SIZE:],
    )


def _next_known(payload: bytes, catalog: dict[int, str], start: int) -> int:
    """Offset of the next dword that is a known id, or len(payload).

    Byte-granular on purpose: a blob whose length is not a multiple of four
    pushes every following entry off the dword grid.
    """
    for off in range(start, len(payload) - 3):
        if struct.unpack_from("<I", payload, off)[0] in catalog:
            return off
    return len(payload)


def _walk_payload(payload: bytes, catalog: dict[int, str]) -> list[Entry]:
    """Walk the payload by looking each stored id up in the catalogue.

    The span of an entry is the distance to the next known id: four bytes for a
    scalar, anything else is a blob whose length is recorded nowhere on disk.
    """
    entries: list[Entry] = []
    pos = 0

    while pos + 4 <= len(payload):
        (stored,) = struct.unpack_from("<I", payload, pos)
        name = catalog.get(stored)
        if name is None:
            raise SaveError(
                f"unknown id 0x{stored:08X} at +0x{pos:X} "
                + f"(entry {len(entries)}); wrong stream file?"
            )
        pos += 4

        end = _next_known(payload, catalog, pos + 4)
        span = end - pos
        if span == 4:
            (raw,) = struct.unpack_from("<I", payload, pos)
            entries.append(Entry(id=stored, name=name, raw=raw))
        else:
            entries.append(Entry(id=stored, name=name, blob=payload[pos:end]))
        pos = end

    if pos != len(payload):
        raise SaveError(f"consumed 0x{pos:X} of 0x{len(payload):X} payload bytes")

    return entries


def read_save(
    path: str | Path,
    stream_path: str | Path = "Levels/global.stream",
    *,
    strict: bool = False,
) -> SaveFile:
    """Parse ``SaveGames.mem`` against ``global.stream``'s declarations.

    With ``strict=False`` a slot that fails to walk keeps its raw payload and an
    empty ``entries`` list instead of raising.
    """
    data = Path(path).read_bytes()
    payload_size, raws = _split_slots(data)
    catalog = build_catalog(stream_path)

    save = SaveFile(payload_size=payload_size, catalog=catalog)

    for i, raw in enumerate(raws):
        slot = _read_header(raw, i)
        save.slots.append(slot)

        if slot.is_empty:
            continue

        try:
            slot.entries = _walk_payload(slot.payload, catalog)
        except SaveError:
            if strict:
                raise

    return save


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Dump a Madagascar SaveGames.mem")
    ap.add_argument("save", help="path to SaveGames.mem")
    ap.add_argument("-s", "--stream", default="Levels/global.stream")
    ap.add_argument("-a", "--all", action="store_true", help="show zero entries too")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    save = read_save(args.save, args.stream, strict=args.strict)
    print(f"payload {save.payload_size} bytes/slot, {len(save.catalog)} known ids")

    for slot in save.slots:
        print(f"\n=== slot {slot.index} ===")
        if slot.is_empty:
            print("  (empty)")
            continue

        ok = "ok" if slot.checksum_ok else "MISMATCH"
        print(f"  version          {slot.version}"
              + f"{'' if slot.version == SAVE_VERSION else '  <-- expected 8'}")
        print(f"  entries          {slot.entry_count}")
        print(f"  language         {slot.language_id}")
        print(f"  percent complete {slot.percent_complete}")
        print(f"  play time        {slot.play_time_seconds}s")
        print(f"  checksum         0x{slot.checksum:08X} ({ok})")
        print(f"  level            {slot.stream_name!r}")

        if not slot.entries:
            print("  <payload did not walk>")
            continue
        for e in slot.entries:
            print(f"    {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
