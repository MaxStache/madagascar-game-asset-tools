"""
txd.py — RenderWare Texture Dictionary (.TXD) Library
========================================================

Read, write, export, and import Renderware TXD files.

"""
from pathlib import Path
from typing import Union
from formats.lib.parser import Parser
from formats.sections import RW_TextureDictionary

def load_txd(filepath: Union[str, Path]) -> RW_TextureDictionary:
    """Load a TXD file from disk

    Args:
        filepath: Path to the .txd file.

    Returns:
        Parsed RW_TextureDictionary.
    """

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

    return RW_TextureDictionary.read(parser, parent=None)


def loads_txd(data: bytes) -> RW_TextureDictionary:
    """Load a TXD from stream

    Args:
        bytestream: Bytes of the .txd.

    Returns:
        Parsed RW_TextureDictionary.
    """

    parser = Parser(data, endian="little")

    return RW_TextureDictionary.read(parser, parent=None)
