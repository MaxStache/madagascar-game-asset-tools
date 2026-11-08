"""Parser and decompiler for TFB script (.ai) files."""

from typing import TYPE_CHECKING

from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs
from tfbscript.script import ScriptFile
from tfbscript.string_table import StringTable, StringTableEntry

if TYPE_CHECKING:
    from tfbscript.editor import editor_from_filepath, open_editor


def __getattr__(name: str):
    # The editor pulls in Qt, which needs a display stack (libEGL etc.).
    # Import it on first use so parsing works on headless machines too.
    if name in ("open_editor", "editor_from_filepath"):
        from tfbscript import editor

        return getattr(editor, name)
    raise AttributeError(f"module 'tfbscript' has no attribute {name!r}")


__all__ = [
    "PayloadReader",
    "Reference",
    "Rhs",
    "ScriptFile",
    "StringTable",
    "StringTableEntry",
    "editor_from_filepath",
    "open_editor",
]
