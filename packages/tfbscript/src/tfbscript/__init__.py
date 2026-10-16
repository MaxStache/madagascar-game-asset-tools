"""Parser and decompiler for TFB script (.ai) files."""

from tfbscript.binary import BinaryReader
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs
from tfbscript.script import ScriptFile
from tfbscript.string_table import StringTable, StringTableEntry

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tfbscript.editor import open_editor, editor_from_filepath


def __getattr__(name: str):
    # The editor pulls in Qt, which needs a display stack (libEGL etc.).
    # Import it on first use so parsing works on headless machines too.
    if name in ("open_editor", "editor_from_filepath"):
        from tfbscript import editor

        return getattr(editor, name)
    raise AttributeError(f"module 'tfbscript' has no attribute {name!r}")


__all__ = [
    "BinaryReader",
    "PayloadReader",
    "Reference",
    "Rhs",
    "ScriptFile",
    "StringTable",
    "StringTableEntry",
    "open_editor",
    "editor_from_filepath"
]
