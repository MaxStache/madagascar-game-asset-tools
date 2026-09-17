"""
rws.py — RenderWare Audio wave dictionary (.RWS) Library
========================================================

Read and write the game's ``*_WavDictXBOX.rws`` wave dictionaries
(chunk ``0x809``). The chunk tree is implemented in
:mod:`madagascar.sections.RWA`.

"""
from pathlib import Path

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import DEFAULT_VERSION_STAMP
from madagascar.sections import RW_WaveDict


def load_rws(filepath: str | Path) -> RW_WaveDict:
    """Load a wave dictionary from disk.

    Args:
        filepath: Path to the .rws file.

    Returns:
        Parsed RW_WaveDict.
    """

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

    return RW_WaveDict.read(parser, parent=None)


def loads_rws(data: bytes) -> RW_WaveDict:
    """Load a wave dictionary from bytes.

    Args:
        data: Bytes of the .rws.

    Returns:
        Parsed RW_WaveDict.
    """

    parser = Parser(data, endian="little")

    return RW_WaveDict.read(parser, parent=None)


def save_rws(
    wavedict: RW_WaveDict,
    filepath: str | Path,
    stamp: int | None = None,
) -> None:
    """Write a wave dictionary back out to disk.

    Args:
        wavedict: The dictionary to serialize.
        filepath: Destination .rws path.
        stamp: Library ID stamp to write. Defaults to the stamp the dictionary
            was read with, so a load/save round-trip is byte-identical.
    """

    if stamp is None:
        stamp = wavedict.header.library_id_stamp or DEFAULT_VERSION_STAMP

    with open(filepath, "wb") as f:
        wavedict.write(f, stamp, parent=None)
