import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, TextIO, cast

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import DEFAULT_VERSION_STAMP, strfunc_func
from madagascar.lib.rw_basics import RW_StreamFunc, RWHeader
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

    def entityByName(self, name: str) -> RW_sf_CreateEntity:
        found = self.entityByNameSoft(name)
        if not found:
            raise AssertionError(
                "find_entity_by_name couldnt find an entity named: " + name
            )
        return found

    def append(self, sf: RW_StreamFunc):
        self.contents.append(sf)

    def updatePlacementNew(self) -> None:
        """Rebuild the sf_PlacementNew table from the entities in the stream.
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

        placement_new.entries = list(counts.items())
        placement_new.entry_count = len(placement_new.entries)

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


def _write_log_attribute(f: TextIO, attr: RW_sf_CreateEntity_Attribute) -> None:
    output = f"\t\tAttribute {attr.command:>3}"

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
            _write_log_attribute(f, attr)

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
