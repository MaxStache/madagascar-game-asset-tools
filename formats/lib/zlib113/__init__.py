"""Byte-exact gzip compression matching the original PS2 tooling.

The game's stream/model files (e.g. KINGOFNY.DFF) were gzipped with zlib
1.1.3 (confirmed from "deflate 1.1.3"/"inflate 1.1.3" copyright strings
embedded in SLUS_210.15). Modern zlib compresses the same input to
different bytes because its match-finding heuristics changed across
versions, so a repack made with Python's stdlib gzip module round-trips
correctly but never matches the original file byte-for-byte.

This module shells out to a vendored, compiled copy of zlib 1.1.3
(see wrapper.c / vendor/) via ctypes to reproduce the original compressor
exactly. Confirmed empirically: level=9, memLevel=8, strategy=0 (all
zlib defaults except level) reproduces KINGOFNY.DFF's compressed body
byte-for-byte.
"""

import ctypes
import platform
import zlib
from pathlib import Path

_LIB_DIR = Path(__file__).parent

if platform.system() == "Darwin":
    _LIB_PATH = _LIB_DIR / "libzlib113.dylib"
elif platform.system() == "Linux":
    _LIB_PATH = _LIB_DIR / "libzlib113.so"
else:
    raise RuntimeError(
        f"No prebuilt zlib113 shared library for platform {platform.system()!r}. "
        f"Run build.sh on a supported platform to produce one."
    )

if not _LIB_PATH.exists():
    raise FileNotFoundError(
        f"{_LIB_PATH} not found. Build it first: formats/lib/zlib113/build.sh"
    )

_lib = ctypes.CDLL(str(_LIB_PATH))
_lib.rw_deflate_113.argtypes = [
    ctypes.c_char_p,
    ctypes.c_ulong,
    ctypes.c_char_p,
    ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong),
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]
_lib.rw_deflate_113.restype = ctypes.c_int

Z_OK = 0


def raw_deflate(data: bytes, level: int = 9, mem_level: int = 8, strategy: int = 0) -> bytes:
    """Compress `data` with vendored zlib 1.1.3, raw DEFLATE (no wrapper)."""
    outcap = len(data) + len(data) // 1000 + 128
    outbuf = ctypes.create_string_buffer(outcap)
    outlen = ctypes.c_ulong(0)

    ret = _lib.rw_deflate_113(
        data, len(data), outbuf, outcap, ctypes.byref(outlen), level, mem_level, strategy
    )
    if ret != Z_OK:
        raise RuntimeError(f"zlib 1.1.3 deflate failed with code {ret}")

    return outbuf.raw[: outlen.value]


def gzip_compress(data: bytes) -> bytes:
    """Gzip `data` matching the original game tooling's exact output.

    Header is written manually (not via zlib's gzio) with MTIME=0, XFL=0,
    OS=0x0B (Windows/NTFS) and no filename, matching the header bytes
    observed in the original shipped assets.
    """
    body = raw_deflate(data)
    crc = zlib.crc32(data) & 0xFFFFFFFF
    size = len(data) & 0xFFFFFFFF

    header = bytes([0x1F, 0x8B, 0x08, 0x00]) + b"\x00\x00\x00\x00" + bytes([0x00, 0x0B])
    trailer = crc.to_bytes(4, "little") + size.to_bytes(4, "little")

    return header + body + trailer
