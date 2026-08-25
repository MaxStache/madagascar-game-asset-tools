import io
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import BinaryIO, TextIO, cast
import uuid

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import DEFAULT_VERSION_STAMP, strfunc_func
from madagascar.lib.rw_basics import RW_Matrix4x4, RW_StreamFunc, RWHeader
from madagascar.streamfuncs import STRFUNC_REGISTRY

import gzip

from madagascar.streamfuncs.stringfuncs.sf_CreateEntity import (
    RW_sf_CreateEntity,
    RW_sf_CreateEntity_Attribute,
)
from madagascar.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import RW_sf_LoadEmbeddedAsset
from madagascar.streamfuncs.stringfuncs.sf_PlacementNew import RW_sf_PlacementNew

__version__ = "1.0.0"

RWSPH_CLASSID = 0x80000000  # Class
RWSPH_INSTANCEID = 0x40000000  # Entity ID
RWSPH_CREATECLASSID = 0x20000000  # Behavior


@dataclass
class RW_StreamFile:
    contents: list[RW_StreamFunc] = field(default_factory=list)

    @staticmethod
    def read(parser: Parser) -> "RW_StreamFile":
        streamf = RW_StreamFile()

        while parser.canRead(RWHeader().binSize):
            peeked_header = RWHeader.peek(parser)
            stream_func_class = STRFUNC_REGISTRY.get(peeked_header.type)

            if stream_func_class is None:
                print(hex(parser.offset))
                raise ValueError(
                    f"Unknown stream function type: {hex(peeked_header.type)}"
                )

            stream_func = stream_func_class.read(parser)
            streamf.contents.append(stream_func)

        return streamf

    def write(self, f: BinaryIO, stamp: int) -> None:
        buf = io.BytesIO()

        for sf in self.contents:
            sf.write(buf, stamp)

        f.write(buf.getvalue())

    def save(self, filepath: str | Path) -> None:
        """WRITE WITH DEFAULT VERSION STAMP"""
        with open(filepath, "wb") as f:
            self.write(f, DEFAULT_VERSION_STAMP)
            f.flush()
            os.fsync(f.fileno())
            
    def verify(self):
        """Do some checks, like:
        - Any Entity (TFB Object)Name or ID used twice
        """

        # DUPE NAME AND ID
        used_entity_ids: list[uuid.UUID] = []
        used_entity_names: list[str] = []
        for e in self.entities():
            # === ID ===
            entityID = e.entityID
            if entityID in used_entity_ids:
                raise ValueError(f"[STREAM VERIFY] Duplicate entity ID: {entityID}")

            used_entity_ids.append(
                entityID
            )

            # === NAME ===

            entityName = e.getAttribute("CTFBCommand",0x00).data.decode("latin1")
            if entityID in used_entity_names:
                raise ValueError(f"[STREAM VERIFY] Duplicate entity name: {entityName}")
            used_entity_names.append(
                entityName
            )

    def entityByNameSoft(self, name: str) -> RW_sf_CreateEntity | None:
        """Finds a RW_sf_CreateEntity by name
        (name = TFB Object name wich is CTFBCommand attr 0)

        Returns None when no name matches
        """
        for sec in self.contents:
            if sec.streamfunc != strfunc_func.sf_CreateEntity:
                continue

            entity = cast(RW_sf_CreateEntity, sec)

            ctfbcommand = entity.find_first_class_with_command("CTFBCommand", 0)
            if not ctfbcommand:
                continue

            ctfbcommand_name = ctfbcommand.find_first_attribute(0)
            if not ctfbcommand_name:
                continue

            entity_name = ctfbcommand_name.data.decode("latin1", errors="ignore")
            entity_name = entity_name.replace("\00", "")
            entity_name = entity_name.replace("\xbf", "")
            if entity_name == name:
                return entity

        return None

    def entities(self) -> list[RW_sf_CreateEntity]:
            """Finds all RW_sf_CreateEntity in stream
            """

            entities: list[RW_sf_CreateEntity] = []

            for sec in self.contents:
                if sec.streamfunc != strfunc_func.sf_CreateEntity:
                    continue
    
                entity = cast(RW_sf_CreateEntity, sec)
    
                entities.append(entity)
    
            return entities

    def entityByName(self, name: str) -> RW_sf_CreateEntity:
        found = self.entityByNameSoft(name)
        if not found:
            raise AssertionError(
                "find_entity_by_name couldnt find an entity named: " + name
            )
        return found

    def append(self, sf: RW_StreamFunc):
        self.contents.append(sf)

    def insertAfter(self, reference: RW_StreamFunc, sf: RW_StreamFunc) -> int:
        """Insert `sf` directly after `reference` in the chunk list.

        Position in the stream matters: the engine processes chunks in order,
        and every original sf_CreateEntity sits just after the
        sf_LoadEmbeddedAsset chunks for the assets it references. A record
        appended at EOF is processed long after those chunks, so prefer placing
        a cloned entity next to the entity it was cloned from.
        """
        for i, sec in enumerate(self.contents):
            if sec is reference:
                self.contents.insert(i + 1, sf)
                return i + 1
        raise ValueError("reference section is not part of this stream")

    def remove(self, sf: RW_StreamFunc) -> int:
        """Remove `sf` from the chunk list. Returns the index it occupied.

        Matched by identity, not equality: the chunks are dataclasses, so two
        distinct records with the same bytes compare equal and `list.remove`
        would drop whichever came first.

        Removing an sf_CreateEntity is enough to stop the engine creating the
        entity - the record is the only thing that spawns it. What stays behind
        is harmless but worth knowing:

        - The sf_LoadEmbeddedAsset chunks for its model/animations are shared
          with other entities and are left alone; a now-unused asset only costs
          load time.
        - `updatePlacementNew()` never lowers a declared count, so the pool
          keeps the freed slot reserved. Over-declaring only wastes bytes.

        What is not harmless is a *name reference*: other entities (LevelHub
        above all) address entities by TFB object name inside their attribute
        data. Check with `referencesToName()` before removing.
        """
        for i, sec in enumerate(self.contents):
            if sec is sf:
                del self.contents[i]
                return i
        raise ValueError("section is not part of this stream")

    def updatePlacementNew(self, headroom: int = 0) -> None:
        """Rebuild the sf_PlacementNew table from the entities in the stream.

        The table declares how many instances of each behaviour the engine
        should reserve, so it must never declare fewer slots than the original
        level did. Two rules keep that true:

        - Existing entries keep their original order, and their declared count
          is never lowered (`max(existing, actual)`). Originals ship entries
          that have no sf_CreateEntity record at all - every retail level
          declares an `AssetHub` with zero instances - and rebuilding purely
          from the entities present would silently delete them.
        - `headroom` adds spare slots to every behaviour that actually has
          instances, for entities the game spawns at runtime.

        New behaviours introduced by a mod are appended after the original ones.
        """
        placement_new = next(
            (sec for sec in self.contents if isinstance(sec, RW_sf_PlacementNew)), None
        )

        if placement_new is None:
            raise ValueError("Stream has no sf_PlacementNew section to update")

        counts: dict[str, int] = {}
        for sec in self.contents:
            if isinstance(sec, RW_sf_CreateEntity):
                counts[sec.behaviour] = counts.get(sec.behaviour, 0) + 1

        entries: list[tuple[str, int]] = []

        for behaviour, declared in placement_new.entries:
            actual = counts.pop(behaviour, None)
            if actual is None:
                # Declared but never instantiated - keep it exactly as it was.
                entries.append((behaviour, declared))
            else:
                entries.append((behaviour, max(declared, actual + headroom)))

        # Behaviours this stream gained that the original table never listed.
        for behaviour, actual in counts.items():
            entries.append((behaviour, actual + headroom))

        placement_new.entries = entries
        placement_new.entry_count = len(entries)

    def write_log(self, output_path: str | Path) -> None:
        """Write a human readable dump of the stream to a text file."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Read a file stream\n\n")

            for idx, sf in enumerate(self.contents):
                streamfunc = sf.streamfunc
                func_name = streamfunc.name if streamfunc else "Unknown"

                f.write(f"{'═' * 20} Sector {idx} {'═' * 20}\n")

                sfBuf = io.BytesIO()
                sf.write(sfBuf, DEFAULT_VERSION_STAMP)
                sfBuf.seek(0)
                headerType = int.from_bytes(sfBuf.read(4), "little")
                headerSize = int.from_bytes(sfBuf.read(4), "little")

                f.write(
                    f"Length: {headerSize} Type: {headerType} ({func_name})\n"
                )

                if isinstance(sf, RW_sf_CreateEntity):
                    _write_log_sf_CreateEntity(f, sf)

                elif isinstance(sf, RW_sf_PlacementNew):
                    _write_log_sf_PlacementNew(f, sf)

                elif isinstance(sf, RW_sf_LoadEmbeddedAsset):
                    _write_log_sf_LoadEmbeddedAsset(f, sf)

                else:
                    f.write("\t[No view defined]\n")
                    raw_data = getattr(sf, "raw_data", None)
                    if raw_data is not None:
                        f.write("\t[Raw Data:]\n")
                        f.write(f"\t\t{raw_data.hex()}\n")


# ═══════════════════════════════════════════════════════
#  Log helpers
# ═══════════════════════════════════════════════════════

# Bytes rendered as-is in the text view of an attribute, everything else
# becomes a space.
_TEXTVIEW_EXTRA_CHARS = frozenset(
    b"_-!?.\\/:()={}[]&$+*#"
)


def _format_matrix4x4(matrix: RW_Matrix4x4, indent: int) -> str:
    """Render a matrix as column aligned rows, continuation lines padded by `indent`."""
    values = [
        [matrix.row1.x, matrix.row1.y, matrix.row1.z, matrix.row1.w],
        [matrix.row2.x, matrix.row2.y, matrix.row2.z, matrix.row2.w],
        [matrix.row3.x, matrix.row3.y, matrix.row3.z, matrix.row3.w],
        [matrix.row4.x, matrix.row4.y, matrix.row4.z, matrix.row4.w],
    ]

    formatted = [[f"{v:.3f}" for v in row] for row in values]
    col_widths = [max(len(row[col]) for row in formatted) for col in range(4)]

    rows = [
        "[" + ", ".join(row[i].ljust(col_widths[i]) for i in range(4)) + "]"
        for row in formatted
    ]

    pad = " " * indent
    body = "".join(f"{pad}{row}\n" for row in rows[1:-1])
    return f"Matrix4x4({rows[0]}\n{body}{pad}{rows[-1]})"


def _write_log_attribute(
    f: TextIO, attr: RW_sf_CreateEntity_Attribute, class_name: str = ""
) -> None:
    output = f"\t\tAttribute {attr.command:>3}"

    # CSystemCommands command 1 is the entity transform, print it as a matrix
    if (
        class_name == "CSystemCommands"
        and attr.command == 0x01
        and len(attr.data) >= 64
    ):
        matrix = RW_Matrix4x4.read(Parser(attr.data, endian="little"))
        indent = len(output.replace("\t", "    ") + ": Matrix4x4(")
        f.write(output + ": " + _format_matrix4x4(matrix, indent) + "\n")
        return

    # Text view: alphanumerics and a few symbols kept, others replaced with space
    textView = ""
    for b in attr.data:
        if (
            (48 <= b <= 57)
            or (65 <= b <= 90)
            or (97 <= b <= 122)
            or b in _TEXTVIEW_EXTRA_CHARS
        ):
            textView += chr(b)
        else:
            textView += " "

    # Hex view: uppercase, 2-digit, space separated
    hexView = " ".join(f"{b:02X}" for b in attr.data)

    output += f": [{textView}][{hexView}]"

    f.write(output + "\n")


def _write_log_sf_CreateEntity(f: TextIO, sf: RW_sf_CreateEntity) -> None:
    f.write("Create Entity Call:\n")

    f.write(f"\tBehaviour:\t{sf.behaviour}\n")
    f.write(f"\tEntity ID:\t{{{sf.entityID}}}\n")

    for atr_class in sf.classes:
        f.write(f"\tClass:\t{atr_class.class_name}\n")

        for attr in atr_class.attributes:
            _write_log_attribute(f, attr, atr_class.class_name)

    f.write(f"\tisGlobal:\t{sf.isGlobal}\n")
    f.write("\n")


def _write_log_sf_PlacementNew(f: TextIO, sf: RW_sf_PlacementNew) -> None:
    f.write("Data:\n")

    f.writelines(f"    {behaviour} Count:{entityCount}\n" for behaviour, entityCount in sf.entries)

    f.write("\n")


def _write_log_sf_LoadEmbeddedAsset(f: TextIO, sf: RW_sf_LoadEmbeddedAsset) -> None:
    f.write("Asset Header:\n")

    f.write(f"\t- Header Size: {sf.headerSize}\n")
    f.write(f"\t- Data Size: {sf.dataSize}\n")

    f.write(f"\t  Asset Name: {sf.name}\n")

    f.write(f"\t- Asset GUID: {sf.guid!s}\n")

    f.write(f"\t  Asset Type: {sf.type}\n")

    f.write(f"\t  Asset File: {sf.filePath}\n")

    f.write(f"\t  Asset Dependecies: {sf.deps}\n")

    f.write("\n")


def load_stream(filepath: str | Path, gzipped: bool = False) -> RW_StreamFile:
    """Load a STREAM level file from disk

    Args:
        filepath: Path to the .stream file.
        gzipped: Whether the file is gzipped or not.

    Returns:
        Parsed Stream File.
    """

    if gzipped:
        with gzip.open(filepath, "rb") as f:
            parser = Parser(f.read(), endian="little")
    else:
        with open(filepath, "rb") as f:
            parser = Parser(f.read(), endian="little")

    stream = RW_StreamFile.read(parser)

    return stream
