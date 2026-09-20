"""
rws.py — RenderWare Audio (.RWS) Library
========================================

Read and write the game's two flavours of ``.rws`` audio file:

"""
from pathlib import Path

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import DEFAULT_VERSION_STAMP, RWSectionType
from madagascar.lib.rw_basics import RWHeader
from madagascar.sections import RW_WaveDict, RWA_Stream

RWS_File = RW_WaveDict | RWA_Stream


def loads_rws(data: bytes) -> RWS_File:
    """Load a wave dictionary or an audio stream from bytes.

    Args:
        data: Bytes of the .rws.

    Returns:
        RW_WaveDict for a 0x809 file, RWA_Stream for a 0x80D one.

    Raises:
        ValueError: The top chunk is neither of those.
    """

    parser = Parser(data, endian="little")

    top = RWHeader.peek(parser)

    if top.type == RWSectionType.rwaID_WAVEDICT.value:
        return RW_WaveDict.read(parser, parent=None)

    if top.type == RWSectionType.rwaID_STREAM.value:
        return RWA_Stream.read(parser, parent=None)

    try:
        found = RWSectionType(top.type).name
    except ValueError:
        found = "unknown"

    raise ValueError(
        f"Not an audio .rws: top chunk is 0x{top.type:03X} ({found}), expected "
        f"0x{RWSectionType.rwaID_WAVEDICT.value:03X} (wave dictionary) or "
        f"0x{RWSectionType.rwaID_STREAM.value:03X} (audio stream)."
    )


def load_rws(filepath: str | Path) -> RWS_File:
    """Load a wave dictionary or an audio stream from disk.

    Args:
        filepath: Path to the .rws file.

    Returns:
        RW_WaveDict for a 0x809 file, RWA_Stream for a 0x80D one.

    Raises:
        ValueError: The top chunk is neither of those.
    """

    with open(filepath, "rb") as f:
        data = f.read()

    return loads_rws(data)


def save_rws(
    rws: RWS_File,
    filepath: str | Path,
    stamp: int | None = None,
) -> None:
    """Write a wave dictionary or an audio stream back out to disk.

    Args:
        rws: The dictionary or stream to serialize.
        filepath: Destination .rws path.
        stamp: Library ID stamp to write. Defaults to the stamp the file was
            read with, so a load/save round-trip is byte-identical.
    """

    if stamp is None:
        stamp = rws.header.library_id_stamp or DEFAULT_VERSION_STAMP

    with open(filepath, "wb") as f:
        rws.write(f, stamp, parent=None)
