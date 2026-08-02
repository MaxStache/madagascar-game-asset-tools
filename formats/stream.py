import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from formats.lib.parser import Parser
from formats.lib.rwConstants import DEFAULT_VERSION_STAMP
from formats.lib.rw_basics import RW_StreamFunc, RWHeader
from formats.streamfuncs import STRFUNC_REGISTRY

import gzip

__version__ = "1.0.0"

RWSPH_CLASSID = 0x80000000  # Class
RWSPH_INSTANCEID = 0x40000000  # Entity ID
RWSPH_CREATECLASSID = 0x20000000  # Behavior

@dataclass
class RW_StreamFile:
    contents: list[RW_StreamFunc] = field(default_factory=list)

    @staticmethod
    def read(parser: Parser) -> "RW_StreamFile":
        streamf = RW_StreamFile()

        while parser.canRead(RWHeader().binSize):
            peeked_header = RWHeader.peek(parser)
            stream_func_class = STRFUNC_REGISTRY.get(peeked_header.type)

            if stream_func_class is None:
                print(hex(parser.offset))
                raise ValueError(f"Unknown stream function type: {hex(peeked_header.type)}")

            stream_func = stream_func_class.read(parser)
            streamf.contents.append(stream_func)

        return streamf

    def write(self, f: BinaryIO, stamp: int) -> None:
        buf = io.BytesIO()

        for sf in self.contents:
            sf.write(buf, stamp)

        f.write(buf.getvalue())

    def save(self, filepath: str | Path) -> None:
        """WRITE WITH DEFAULT VERSION STAMP"""
        with open(filepath, "wb") as f:
            self.write(f, DEFAULT_VERSION_STAMP)

def load_stream(filepath: str | Path, gzipped: bool = False) -> RW_StreamFile:
    """Load a STREAM level file from disk

    Args:
        filepath: Path to the .stream file.
        gzipped: Whether the file is gzipped or not.

    Returns:
        Parsed Stream File.
    """

    if gzipped:
        with gzip.open(filepath, "rb") as f:
            parser = Parser(f.read(), endian="little")
    else:
        with open(filepath, "rb") as f:
            parser = Parser(f.read(), endian="little")

    stream = RW_StreamFile.read(parser)

    return stream