"""Parser and decompiler for TFB script (.ai) files."""

from tfbscript.binary import BinaryReader
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference
from tfbscript.rhs import Rhs
from tfbscript.script import ScriptFile
from tfbscript.string_table import StringTable, StringTableEntry
from tfbscript.editor import open_editor, editor_from_filepath

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
