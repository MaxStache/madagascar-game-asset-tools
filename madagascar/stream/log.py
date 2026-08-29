"""Human readable text dump of a stream file."""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO, cast
from collections.abc import Callable

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import DEFAULT_VERSION_STAMP
from madagascar.lib.rw_basics import RW_Matrix4x4, RW_StreamFunc
from madagascar.streamfuncs.stringfuncs.sf_CreateEntity import (
    RW_sf_CreateEntity,
    RW_sf_CreateEntity_Attribute,
)
from madagascar.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import (
    RW_sf_LoadEmbeddedAsset,
)
from madagascar.streamfuncs.stringfuncs.sf_PlacementNew import RW_sf_PlacementNew

if TYPE_CHECKING:
    from madagascar.stream.file import RW_StreamFile

# Bytes rendered as-is in the text view of an attribute, everything else
# becomes a space.
_TEXTVIEW_EXTRA_CHARS = frozenset(rb"_-!?.\/:()={}[]&$+*#")


class StreamLogMixin:
    """`write_log` mixed into `RW_StreamFile`."""

    contents: list[RW_StreamFunc]

    def write_log(self, output_path: str | Path) -> None:
        """Write a human readable dump of the stream to a text file."""
        stream = cast("RW_StreamFile", self)

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

                f.write(f"Length: {headerSize} Type: {headerType} ({func_name})\n")

                for section_type, writer in _SECTION_WRITERS:
                    if isinstance(sf, section_type):
                        writer(f, sf, stream)
                        break
                else:
                    _write_unknown(f, sf, stream)


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


def _write_attribute(
    f: TextIO,
    attr: RW_sf_CreateEntity_Attribute,
    stream: RW_StreamFile,
    class_name: str = "",
) -> None:
    output = f"\t\tAttribute {attr.command:>3}"

    # CSystemCommands command 1 is the entity transform, print it as a matrix
    if class_name == "CSystemCommands" and attr.command == 0x01 and len(attr.data) >= 64:
        matrix = RW_Matrix4x4.read(Parser(attr.data, endian="little"))
        indent = len(output.replace("\t", "    ") + ": Matrix4x4(")
        f.write(output + ": " + _format_matrix4x4(matrix, indent) + "\n")
        return

    if class_name == "CSystemCommands" and attr.command == 0x00:
        guid = Parser(attr.data, endian="little").readGUID()
        resolved = stream.assetByIDSoft(guid)

        if resolved is None:
            ref_string = "MISSING"
        else:
            ref_string = f"{resolved.type} - {resolved.name}"
        f.write("\t\tCMD 0: Attach Asset {" + str(guid) + f"}} ( {ref_string} ) \n")
        return

    # Text view: alphanumerics and a few symbols kept, others replaced with space
    textView = "".join(
        chr(b)
        if (48 <= b <= 57)
        or (65 <= b <= 90)
        or (97 <= b <= 122)
        or b in _TEXTVIEW_EXTRA_CHARS
        else " "
        for b in attr.data
    )

    # Hex view: uppercase, 2-digit, space separated
    hexView = " ".join(f"{b:02X}" for b in attr.data)

    f.write(f"{output}: [{textView}][{hexView}]\n")


def _write_createEntity(f: TextIO, sf: RW_sf_CreateEntity, stream: RW_StreamFile) -> None:
    f.write("Create Entity Call:\n")

    f.write(f"\tBehaviour:\t{sf.behaviour}\n")
    f.write(f"\tEntity ID:\t{{{sf.entityID}}}\n")

    for atr_class in sf.classes:
        f.write(f"\tClass:\t{atr_class.class_name}\n")

        for attr in atr_class.attributes:
            _write_attribute(f, attr, stream, atr_class.class_name)

    f.write(f"\tisGlobal:\t{sf.isGlobal}\n")
    f.write("\n")


def _write_placementNew(f: TextIO, sf: RW_sf_PlacementNew, stream: RW_StreamFile) -> None:
    f.write("Data:\n")

    f.writelines(
        f"    {behaviour} Count:{entityCount}\n" for behaviour, entityCount in sf.entries
    )

    f.write("\n")


def _write_loadEmbeddedAsset(f: TextIO, sf: RW_sf_LoadEmbeddedAsset, stream: RW_StreamFile) -> None:
    f.write("Asset Header:\n")

    f.write(f"\t- Header Size: {sf.headerSize}\n")
    f.write(f"\t- Data Size: {sf.dataSize}\n")
    f.write(f"\t  Asset Name: {sf.name}\n")
    f.write(f"\t- Asset GUID: {sf.guid!s}\n")
    f.write(f"\t  Asset Type: {sf.type}\n")
    f.write(f"\t  Asset File: {sf.filePath}\n")
    f.write(f"\t  Asset Dependecies: {sf.deps}\n")

    f.write("\n")


def _write_unknown(f: TextIO, sf: RW_StreamFunc, stream: RW_StreamFile) -> None:
    f.write("\t[No view defined]\n")

    raw_data = getattr(sf, "raw_data", None)
    if raw_data is not None:
        f.write("\t[Raw Data:]\n")
        f.write(f"\t\t{raw_data.hex()}\n")


# Add an entry here to give a stream function its own view in the dump.
# Anything not listed falls back to a raw hex dump.
_SECTION_WRITERS: list[tuple[type, Callable[[TextIO, Any, RW_StreamFile], None]]] = [
    (RW_sf_CreateEntity, _write_createEntity),
    (RW_sf_PlacementNew, _write_placementNew),
    (RW_sf_LoadEmbeddedAsset, _write_loadEmbeddedAsset),
]

