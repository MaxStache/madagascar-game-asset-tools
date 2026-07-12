"""
rwDFF.py — RenderWare Model (.DFF) Library
========================================================

Read, write, export, and import Renderware DFF files.

"""
from pathlib import Path
from typing import Union
from formats.lib.parser import Parser
from formats.sections import RW_Clump

def load_dff(filepath: Union[str, Path]) -> RW_Clump:
    """Load a DFF file from disk

    Args:
        filepath: Path to the .dff file.

    Returns:
        Parsed DFF.
    """

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

    return RW_Clump.read(parser, parent=None)

def loads_dff(data: bytes) -> RW_Clump:
    """Load a DFF from stream

    Args:
        bytestream: Bytes of the .dff.

    Returns:
        Parsed RW_Clump.
    """

    parser = Parser(data, endian="little")

    return RW_Clump.read(parser, parent=None)
