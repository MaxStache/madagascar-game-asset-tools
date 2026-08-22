"""
bsp.py — RenderWare World (.BSP) Library
========================================================

Read, write, (export, and import) Renderware BSP files.

"""
from pathlib import Path
from typing import Union
from madagascar.lib.parser import Parser
from madagascar.sections import RW_World

def load_bsp(filepath: Union[str, Path]) -> RW_World:
    """Load a BSP file from disk

    Args:
        filepath: Path to the .bsp file.

    Returns:
        Parsed BSP.
    """

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

    return RW_World.read(parser, parent=None)

def loads_bsp(data: bytes) -> RW_World:
    """Load a BSP from stream

    Args:
        bytestream: Bytes of the .bsp.

    Returns:
        Parsed RW_World.
    """

    parser = Parser(data, endian="little")

    return RW_World.read(parser, parent=None)