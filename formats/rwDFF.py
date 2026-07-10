"""
rwDFF.py — RenderWare Model (.DFF) Library
========================================================

Read, write, export, and import Renderware DFF files.

"""
from pathlib import Path
from typing import Union
from lib.parser import Parser
from sections import RW_Clump

__version__ = "1.0.0"

def load_dff(filepath: Union[str, Path]) -> RW_Clump:
    """Load a DFF file from disk

    Args:
        filepath: Path to the .dff file.

    Returns:
        Parsed DFF.
    """

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

    return RW_Clump.read(parser, parent_type=None)
