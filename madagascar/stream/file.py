"""The `RW_StreamFile` container: parsing, writing and loading a .stream file."""

import gzip
import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import DEFAULT_VERSION_STAMP
from madagascar.lib.rw_basics import RW_StreamFunc, RWHeader
from madagascar.streamfuncs import STRFUNC_REGISTRY

from madagascar.stream.edit import StreamEditMixin
from madagascar.stream.log import StreamLogMixin
from colorama import Fore, init

init(autoreset=True)

@dataclass
class RW_StreamFile(StreamEditMixin, StreamLogMixin):
    contents: list[RW_StreamFunc] = field(default_factory=list)

    _INTERNAL_CHECKING_VERIFIED = False
    _INTERNAL_CHECKING_PLACEMENTDIRTY = False
    _INTERNAL_CHECKING_PLACEMENTUPDATED = False

    @staticmethod
    def read(parser: Parser) -> "RW_StreamFile":
        streamf = RW_StreamFile()

        while parser.canRead(RWHeader().binSize):
            peeked_header = RWHeader.peek(parser)
            stream_func_class = STRFUNC_REGISTRY.get(peeked_header.type)

            if stream_func_class is None:
                raise ValueError(
                    f"Unknown stream function type {hex(peeked_header.type)} "
                    + f"at offset {hex(parser.offset)}"
                )

            streamf.contents.append(stream_func_class.read(parser))

        return streamf

    def write(self, f: BinaryIO, stamp: int) -> None:
        buf = io.BytesIO()

        for sf in self.contents:
            sf.write(buf, stamp)

        f.write(buf.getvalue())

    def save(self, filepath: str | Path) -> None:
        """WRITE WITH DEFAULT VERSION STAMP"""
        if not self._INTERNAL_CHECKING_VERIFIED:
            print(Fore.LIGHTRED_EX + "WARN: STREAM WAS NEVER VERIFIES, we recomment running a few quick checks by running 'level_stream.verify()' before save")
        with open(filepath, "wb") as f:
            self.write(f, DEFAULT_VERSION_STAMP)
            f.flush()
            os.fsync(f.fileno())


def load_stream(filepath: str | Path, gzipped: bool = False) -> RW_StreamFile:
    """Load a STREAM level file from disk

    Args:
        filepath: Path to the .stream file.
        gzipped: Whether the file is gzipped or not.

    Returns:
        Parsed Stream File.
    """
    opener = gzip.open if gzipped else open

    with opener(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

    return RW_StreamFile.read(parser)
