"""
anm.py — RenderWare AnimAnimation (.ANM) Library
========================================================

Read and write Renderware ANM files.

"""
from pathlib import Path
from typing import Union
from formats.lib.parser import Parser
from formats.sections import RW_AnimAnimation

def load_anm(filepath: Union[str, Path]) -> RW_AnimAnimation:
    """Load a ANM file from disk

    Args:
        filepath: Path to the .anm file.

    Returns:
        Parsed RW_AnimAnimation.
    """

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

    return RW_AnimAnimation.read(parser, parent=None)

def loads_bsp(data: bytes) -> RW_AnimAnimation:
    """Load a ANM from stream

    Args:
        bytestream: Bytes of the .anm.

    Returns:
        Parsed RW_AnimAnimation.
    """

    parser = Parser(data, endian="little")

    return RW_AnimAnimation.read(parser, parent=None)