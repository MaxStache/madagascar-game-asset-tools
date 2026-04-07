"""
rwtxd.py — RenderWare Texture Dictionary (.TXD) Library
========================================================

Read, write, decode, and encode Xbox-platform TXD files.
Uses Pillow for PNG import/export.

Usage:
    import rwtxd

    # Read
    txd = rwtxd.load("file.txd")
    for tex in txd.textures:
        print(tex.name, tex.width, tex.height)

    # Decode to RGBA
    rgba = rwtxd.decode(tex)

    # Export to PNG
    rwtxd.export_png(tex, "output.png")

    # Create from scratch
    txd = rwtxd.TextureDictionary()
    tex = rwtxd.create_texture("mytex", rgba_bytes, 64, 64)
    txd.textures.append(tex)
    rwtxd.save(txd, "output.txd")

    # Import from PNG
    tex = rwtxd.import_png("input.png", name="mytex")
"""

import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union
from enum import Enum

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import numpy as np
except ImportError:
    np = None

__version__ = "1.0.0"


# ═══════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════

# Chunk types
CHUNK_STRUCT = 0x01
CHUNK_STRING = 0x02
CHUNK_EXTENSION = 0x03
CHUNK_TEXTURENATIVE = 0x15
CHUNK_TEXDICTIONARY = 0x16
CHUNK_SKYMIPMAP = 0x110

# Platform IDs
PLATFORM_OGL = 2
PLATFORM_PS2 = 4
PLATFORM_XBOX = 5
PLATFORM_D3D8 = 8
PLATFORM_D3D9 = 9
PLATFORM_PS2FOURCC = 0x00325350

# Raster pixel formats (bits 8-11)
RASTER_DEFAULT = 0x0000
RASTER_1555 = 0x0100
RASTER_565 = 0x0200
RASTER_4444 = 0x0300
RASTER_LUM8 = 0x0400
RASTER_8888 = 0x0500
RASTER_888 = 0x0600
RASTER_16 = 0x0700
RASTER_24 = 0x0800
RASTER_32 = 0x0900
RASTER_555 = 0x0A00

# Raster flags
RASTER_AUTOMIPMAP = 0x1000
RASTER_PAL8 = 0x2000
RASTER_PAL4 = 0x4000
RASTER_MIPMAP = 0x8000
RASTER_MASK = 0x0F00

# Default RW version stamp (GTA San Andreas = 3.6.0.3 / build 0xFFFF)
DEFAULT_VERSION_STAMP = 0x1C02000F

PLATFORM_NAMES = {
    2: "OpenGL",
    4: "PS2",
    5: "Xbox",
    8: "D3D8",
    9: "D3D9",
    0x00325350: "PS2 (FourCC)",
}

RASTER_FORMAT_NAMES = {
    0x0000: "DEFAULT",
    0x0100: "1555",
    0x0200: "565",
    0x0300: "4444",
    0x0400: "LUM8",
    0x0500: "8888",
    0x0600: "888",
    0x0700: "16",
    0x0800: "24",
    0x0900: "32",
    0x0A00: "555",
}


# ═══════════════════════════════════════════════════════
#  Data Structures
# ═══════════════════════════════════════════════════════


@dataclass
class RWHeader:
    type: int = 0
    size: int = 0
    library_id_stamp: int = DEFAULT_VERSION_STAMP

    def pack(self) -> bytes:
        return struct.pack("<III", self.type, self.size, self.library_id_stamp)

    @staticmethod
    def read(f) -> "RWHeader":
        data = f.read(12)
        if len(data) < 12:
            raise EOFError("Unexpected end of file reading RWHeader")
        t, s, lib = struct.unpack("<III", data)
        return RWHeader(type=t, size=s, library_id_stamp=lib)

    @property
    def version(self) -> str:
        if self.library_id_stamp & 0xFFFF0000:
            v = (self.library_id_stamp >> 14 & 0x3FF00) + 0x30000
            v |= self.library_id_stamp >> 16 & 0x3F
            return f"{(v >> 16) & 0xF}.{(v >> 12) & 0xF}.{(v >> 8) & 0xF}.{v & 0xFF}"
        return "3.1.0.0"


@dataclass
class PaletteEntry:
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255


@dataclass
class MipmapLevel:
    width: int = 0
    height: int = 0
    data_size: int = 0
    texels: bytes = b""


@dataclass
class NativeTexture:
    platform_id: int = PLATFORM_XBOX
    filter_mode: int = 0x3302
    name: str = ""
    mask_name: str = ""
    raster_format: int = 0
    has_alpha: int = 0
    width: int = 0
    height: int = 0
    depth: int = 0
    mipmap_count: int = 0
    tex_code_type: int = 4
    dxt_compression: int = 0
    palette: list = field(default_factory=list)
    mipmaps: list = field(default_factory=list)
    extension_data: bytes = b"\xDD\x00\x00\x80\x0C\x00\x00\x00\x0F\x00\x02\x1C\x04\x00\x0F\x0F\x00\x00\x00\x00\x01\x00\x00\x00"
    version_stamp: int = DEFAULT_VERSION_STAMP
    # Raw bytes for byte-perfect round-trip
    _raw_struct_data: Optional[bytes] = None
    _raw_ext_stamp: int = DEFAULT_VERSION_STAMP
    _xbox_texelDataSize: int = 0

    @property
    def pixel_format(self) -> int:
        return self.raster_format & RASTER_MASK

    @property
    def pixel_format_name(self) -> str:
        return RASTER_FORMAT_NAMES.get(self.pixel_format, f"0x{self.pixel_format:04X}")

    @property
    def is_palettized(self) -> bool:
        return bool(self.raster_format & (RASTER_PAL8 | RASTER_PAL4))

    @property
    def is_compressed(self) -> bool:
        return self.dxt_compression != 0

    @property
    def raster_flags_str(self) -> str:
        flags = []
        if self.raster_format & RASTER_PAL8:
            flags.append("PAL8")
        if self.raster_format & RASTER_PAL4:
            flags.append("PAL4")
        if self.raster_format & RASTER_MIPMAP:
            flags.append("MIPMAP")
        if self.raster_format & RASTER_AUTOMIPMAP:
            flags.append("AUTOMIPMAP")
        return " | ".join(flags) if flags else "none"


@dataclass
class TextureDictionary:
    textures: list = field(default_factory=list)
    device_id: int = 0
    version_stamp: int = DEFAULT_VERSION_STAMP
    _txd_extension_data: bytes = b""


# ═══════════════════════════════════════════════════════
#  Binary I/O helpers
# ═══════════════════════════════════════════════════════


def _read_u8(f) -> int:
    return struct.unpack("<B", f.read(1))[0]


def _read_u16(f) -> int:
    return struct.unpack("<H", f.read(2))[0]


def _read_u32(f) -> int:
    return struct.unpack("<I", f.read(4))[0]


def _write_u8(f, v):
    f.write(struct.pack("<B", v))


def _write_u16(f, v):
    f.write(struct.pack("<H", v))


def _write_u32(f, v):
    f.write(struct.pack("<I", v))


def _read_fixed_string(f, length: int) -> str:
    raw = f.read(length)
    null = raw.find(b"\x00")
    return (raw[:null] if null >= 0 else raw).decode("ascii", errors="replace")


def _write_fixed_string(f, s: str, length: int):
    encoded = s.encode("ascii", errors="replace")[: length - 1]
    f.write(encoded + b"\x00" * (length - len(encoded)))


def _write_header(f, chunk_type: int, size: int, stamp: int = DEFAULT_VERSION_STAMP):
    f.write(struct.pack("<III", chunk_type, size, stamp))

class FilterMode(Enum):
    FILTER_NONE = 0x00
    FILTER_NEAREST = 0x01
    FILTER_LINEAR = 0x02
    FILTER_MIP_NEAREST = 0x03
    FILTER_MIP_LINEAR = 0x04
    FILTER_LINEAR_MIP_NEAREST = 0x05
    FILTER_LINEAR_MIP_LINEAR = 0x06


class AddressingMode(Enum):
    WRAP_NONE = 0x00
    WRAP_WRAP = 0x01
    WRAP_MIRROR = 0x02
    WRAP_CLAMP = 0x03

def assemble_filter_mode(
    filterMode: FilterMode, uAddressing: AddressingMode, vAddressing: AddressingMode
) -> int:
    # validate ranges
    if not (0 <= filterMode < 2**8):
        raise ValueError("filterMode must fit in 8 bits (0-255)")
    if not (0 <= uAddressing < 2**4):
        raise ValueError("uAddressing must fit in 4 bits (0-15)")
    if not (0 <= vAddressing < 2**4):
        raise ValueError("vAddressing must fit in 4 bits (0-15)")

    value = (
        (filterMode) | (uAddressing << 8) | (vAddressing << 12)
        # pad is 0, so no shift needed
    )

    return value
def disassemble_filter_mode(value: int) -> tuple[int, int, int]:
    # validate 16-bit range if desired
    if not (0 <= value < 2**16):
        raise ValueError("value must fit in 16 bits (0-65535)")

    filterMode = value & 0xFF          # 8 bits
    uAddressing = (value >> 8) & 0xF   # next 4 bits
    vAddressing = (value >> 12) & 0xF  # next 4 bits

    return filterMode, uAddressing, vAddressing



# ═══════════════════════════════════════════════════════
#  Swizzle / Unswizzle (Xbox Morton Z-order)
# ═══════════════════════════════════════════════════════


def _spread_bits(v: int) -> int:
    v = v & 0x0000FFFF
    v = (v | (v << 8)) & 0x00FF00FF
    v = (v | (v << 4)) & 0x0F0F0F0F
    v = (v | (v << 2)) & 0x33333333
    v = (v | (v << 1)) & 0x55555555
    return v


def _compact_bits(v: int) -> int:
    v = v & 0x55555555
    v = (v | (v >> 1)) & 0x33333333
    v = (v | (v >> 2)) & 0x0F0F0F0F
    v = (v | (v >> 4)) & 0x00FF00FF
    v = (v | (v >> 8)) & 0x0000FFFF
    return v


def _morton_encode(x: int, y: int) -> int:
    return _spread_bits(x) | (_spread_bits(y) << 1)


def _morton_decode(z: int) -> tuple:
    return _compact_bits(z), _compact_bits(z >> 1)


def unswizzle(data: bytes, width: int, height: int, bpp: int = 1) -> bytearray:
    """Unswizzle Xbox Z-order (Morton curve) texture data.

    Args:
        data: Swizzled texel data.
        width: Texture width in pixels.
        height: Texture height in pixels.
        bpp: Bytes per pixel (1=palettized, 2=16bit, 4=32bit).

    Returns:
        Linear (scanline-order) texel data.
    """
    out = bytearray(width * height * bpp)

    if width >= height:
        block_size = height
        x_blocks = width // block_size if block_size else 1
        y_blocks = 1
    else:
        block_size = width
        x_blocks = 1
        y_blocks = height // block_size if block_size else 1

    pixels_per_block = block_size * block_size

    for by in range(y_blocks):
        for bx in range(x_blocks):
            src_base = (by * x_blocks + bx) * pixels_per_block * bpp
            for y in range(block_size):
                for x in range(block_size):
                    morton = _morton_encode(x, y)
                    src = src_base + morton * bpp
                    ox = bx * block_size + x
                    oy = by * block_size + y
                    dst = (oy * width + ox) * bpp
                    if src + bpp <= len(data):
                        out[dst : dst + bpp] = data[src : src + bpp]

    return out


def swizzle(data: bytes, width: int, height: int, bpp: int = 1) -> bytearray:
    """Swizzle linear texel data into Xbox Z-order (Morton curve) layout.

    Args:
        data: Linear (scanline-order) texel data.
        width: Texture width in pixels.
        height: Texture height in pixels.
        bpp: Bytes per pixel.

    Returns:
        Swizzled texel data.
    """
    out = bytearray(width * height * bpp)

    if width >= height:
        block_size = height
        x_blocks = width // block_size if block_size else 1
        y_blocks = 1
    else:
        block_size = width
        x_blocks = 1
        y_blocks = height // block_size if block_size else 1

    pixels_per_block = block_size * block_size

    for by in range(y_blocks):
        for bx in range(x_blocks):
            dst_base = (by * x_blocks + bx) * pixels_per_block * bpp
            for y in range(block_size):
                for x in range(block_size):
                    morton = _morton_encode(x, y)
                    dst = dst_base + morton * bpp
                    ox = bx * block_size + x
                    oy = by * block_size + y
                    src = (oy * width + ox) * bpp
                    if dst + bpp <= len(out) and src + bpp <= len(data):
                        out[dst : dst + bpp] = data[src : src + bpp]

    return out


# ═══════════════════════════════════════════════════════
#  DXT Codec
# ═══════════════════════════════════════════════════════


def _decode_rgb565(c: int) -> tuple:
    return (
        ((c >> 11) & 0x1F) * 255 // 31,
        ((c >> 5) & 0x3F) * 255 // 63,
        (c & 0x1F) * 255 // 31,
    )


def _encode_rgb565(r: int, g: int, b: int) -> int:
    return ((r * 31 // 255) << 11) | ((g * 63 // 255) << 5) | (b * 31 // 255)


def _decode_dxt_color_block(block: bytes) -> list:
    c0 = struct.unpack_from("<H", block, 0)[0]
    c1 = struct.unpack_from("<H", block, 2)[0]
    r0, g0, b0 = _decode_rgb565(c0)
    r1, g1, b1 = _decode_rgb565(c1)

    colors = [(r0, g0, b0, 255), (r1, g1, b1, 255)]
    if c0 > c1:
        colors.append(((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255))
        colors.append(((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255))
    else:
        colors.append(((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255))
        colors.append((0, 0, 0, 0))

    lookup = struct.unpack_from("<I", block, 4)[0]
    pixels = []
    for i in range(16):
        pixels.append(colors[(lookup >> (i * 2)) & 0x3])
    return pixels


def decode_dxt1(data: bytes, width: int, height: int) -> bytes:
    """Decode DXT1 compressed data to RGBA."""
    rgba = bytearray(width * height * 4)
    block_idx = 0
    for by in range(0, height, 4):
        for bx in range(0, width, 4):
            pixels = _decode_dxt_color_block(data[block_idx : block_idx + 8])
            block_idx += 8
            for py in range(4):
                for px in range(4):
                    x, y = bx + px, by + py
                    if x < width and y < height:
                        off = (y * width + x) * 4
                        rgba[off : off + 4] = bytes(pixels[py * 4 + px])
    return bytes(rgba)


def decode_dxt3(data: bytes, width: int, height: int) -> bytes:
    """Decode DXT3 compressed data to RGBA."""
    rgba = bytearray(width * height * 4)
    block_idx = 0
    for by in range(0, height, 4):
        for bx in range(0, width, 4):
            alpha_block = data[block_idx : block_idx + 8]
            block_idx += 8
            pixels = _decode_dxt_color_block(data[block_idx : block_idx + 8])
            block_idx += 8
            for py in range(4):
                alpha_row = struct.unpack_from("<H", alpha_block, py * 2)[0]
                for px in range(4):
                    x, y = bx + px, by + py
                    if x < width and y < height:
                        p = pixels[py * 4 + px]
                        a = ((alpha_row >> (px * 4)) & 0xF) * 255 // 15
                        off = (y * width + x) * 4
                        rgba[off : off + 4] = bytes((p[0], p[1], p[2], a))
    return bytes(rgba)


def decode_dxt5(data: bytes, width: int, height: int) -> bytes:
    """Decode DXT5 compressed data to RGBA."""
    rgba = bytearray(width * height * 4)
    block_idx = 0
    for by in range(0, height, 4):
        for bx in range(0, width, 4):
            a0 = data[block_idx]
            a1 = data[block_idx + 1]
            alpha_bits = int.from_bytes(data[block_idx + 2 : block_idx + 8], "little")
            block_idx += 8

            alphas = [a0, a1]
            if a0 > a1:
                for j in range(1, 7):
                    alphas.append(((7 - j) * a0 + j * a1) // 7)
            else:
                for j in range(1, 5):
                    alphas.append(((5 - j) * a0 + j * a1) // 5)
                alphas.extend([0, 255])

            pixels = _decode_dxt_color_block(data[block_idx : block_idx + 8])
            block_idx += 8

            for py in range(4):
                for px in range(4):
                    x, y = bx + px, by + py
                    if x < width and y < height:
                        p = pixels[py * 4 + px]
                        bit_pos = (py * 4 + px) * 3
                        a_idx = (alpha_bits >> bit_pos) & 0x7
                        off = (y * width + x) * 4
                        rgba[off : off + 4] = bytes((p[0], p[1], p[2], alphas[a_idx]))
    return bytes(rgba)


def encode_dxt1(rgba: bytes, width: int, height: int) -> bytes:
    """Encode RGBA data to DXT1. Simple endpoint selection (min/max color)."""
    out = bytearray()
    for by in range(0, height, 4):
        for bx in range(0, width, 4):
            block_pixels = []
            for py in range(4):
                for px in range(4):
                    x = min(bx + px, width - 1)
                    y = min(by + py, height - 1)
                    off = (y * width + x) * 4
                    block_pixels.append(
                        (rgba[off], rgba[off + 1], rgba[off + 2], rgba[off + 3])
                    )

            # Find min/max colors as endpoints
            min_c = [255, 255, 255]
            max_c = [0, 0, 0]
            for p in block_pixels:
                for c in range(3):
                    min_c[c] = min(min_c[c], p[c])
                    max_c[c] = max(max_c[c], p[c])

            c0 = _encode_rgb565(max_c[0], max_c[1], max_c[2])
            c1 = _encode_rgb565(min_c[0], min_c[1], min_c[2])

            if c0 < c1:
                c0, c1 = c1, c0
                max_c, min_c = min_c, max_c

            if c0 == c1:
                out += struct.pack("<HHI", c0, c1, 0)
                continue

            # Build 4-color palette
            colors = [
                max_c,
                min_c,
                [(2 * max_c[i] + min_c[i]) // 3 for i in range(3)],
                [(max_c[i] + 2 * min_c[i]) // 3 for i in range(3)],
            ]

            # Find closest color index for each pixel
            lookup = 0
            for i, p in enumerate(block_pixels):
                best_idx = 0
                best_dist = float("inf")
                for ci, col in enumerate(colors):
                    dist = sum((p[c] - col[c]) ** 2 for c in range(3))
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = ci
                lookup |= best_idx << (i * 2)

            out += struct.pack("<HHI", c0, c1, lookup)

    return bytes(out)


# ═══════════════════════════════════════════════════════
#  Decode texture → RGBA
# ═══════════════════════════════════════════════════════


def decode(tex: NativeTexture, mipmap_index: int = 0) -> bytes:
    """Decode a NativeTexture mipmap level to raw RGBA bytes.

    Args:
        tex: The texture to decode.
        mipmap_index: Which mipmap level (0 = full resolution).

    Returns:
        RGBA pixel data as bytes, length = width * height * 4.
    """
    mip = tex.mipmaps[mipmap_index]
    w, h = mip.width, mip.height

    if tex.palette and tex.dxt_compression == 0:
        indices = unswizzle(mip.texels, w, h, bpp=1)
        rgba = bytearray(w * h * 4)
        for i, idx in enumerate(indices):
            if idx < len(tex.palette):
                p = tex.palette[idx]
                rgba[i * 4 : i * 4 + 4] = bytes((p.r, p.g, p.b, p.a))
        return bytes(rgba)

    elif tex.dxt_compression == 0 and not tex.palette:
        if tex.depth == 32:
            raw = unswizzle(mip.texels, w, h, bpp=4)
            rgba = bytearray(w * h * 4)
            for i in range(w * h):
                off = i * 4
                rgba[off] = raw[off + 2]  # R ← B
                rgba[off + 1] = raw[off + 1]  # G
                rgba[off + 2] = raw[off]  # B ← R
                rgba[off + 3] = raw[off + 3]  # A
            return bytes(rgba)

        elif tex.depth == 16:
            raw = unswizzle(mip.texels, w, h, bpp=2)
            rgba = bytearray(w * h * 4)
            fmt = tex.raster_format & RASTER_MASK
            for i in range(w * h):
                pixel = struct.unpack_from("<H", raw, i * 2)[0]
                if fmt == RASTER_1555:
                    a = 255 if (pixel >> 15) & 1 else 0
                    r = ((pixel >> 10) & 0x1F) * 255 // 31
                    g = ((pixel >> 5) & 0x1F) * 255 // 31
                    b = (pixel & 0x1F) * 255 // 31
                elif fmt == RASTER_565:
                    r = ((pixel >> 11) & 0x1F) * 255 // 31
                    g = ((pixel >> 5) & 0x3F) * 255 // 63
                    b = (pixel & 0x1F) * 255 // 31
                    a = 255
                elif fmt == RASTER_4444:
                    a = ((pixel >> 12) & 0xF) * 255 // 15
                    r = ((pixel >> 8) & 0xF) * 255 // 15
                    g = ((pixel >> 4) & 0xF) * 255 // 15
                    b = (pixel & 0xF) * 255 // 15
                else:
                    r = g = b = a = 0
                rgba[i * 4 : i * 4 + 4] = bytes((r, g, b, a))
            return bytes(rgba)

    elif tex.dxt_compression in (1, 0x0C):
        return decode_dxt1(mip.texels, w, h)

    elif tex.dxt_compression == 3:
        return decode_dxt3(mip.texels, w, h)

    elif tex.dxt_compression == 5:
        return decode_dxt5(mip.texels, w, h)

    raise ValueError(
        f"Unsupported format: depth={tex.depth}, "
        f"dxt={tex.dxt_compression}, palette={len(tex.palette)}"
    )


# ═══════════════════════════════════════════════════════
#  Read TXD
# ═══════════════════════════════════════════════════════


def _read_xbox_texture(f) -> NativeTexture:
    tex = NativeTexture()

    native_header = RWHeader.read(f)
    if native_header.type != CHUNK_TEXTURENATIVE:
        raise ValueError(
            f"Expected TEXTURENATIVE (0x{CHUNK_TEXTURENATIVE:02X}), "
            f"got 0x{native_header.type:02X}"
        )

    tex.version_stamp = native_header.library_id_stamp
    struct_header = RWHeader.read(f)
    struct_start = f.tell()  # noqa: F841

    # Store entire raw struct data for byte-perfect round-trip
    tex._raw_struct_data = f.read(struct_header.size)
    struct_end = f.tell() # noqa: F841

    # Now parse the fields from the raw data
    r = io.BytesIO(tex._raw_struct_data)

    tex.platform_id = _read_u32(r)
    if tex.platform_id != PLATFORM_XBOX:
        raise ValueError(f"Expected Xbox platform (5), got {tex.platform_id}")

    tex.filter_mode = _read_u32(r)
    tex.name = _read_fixed_string(r, 32)
    tex.mask_name = _read_fixed_string(r, 32)
    tex.raster_format = _read_u32(r)
    tex.has_alpha = _read_u32(r)
    tex.width = _read_u16(r)
    tex.height = _read_u16(r)
    tex.depth = _read_u8(r)
    tex.mipmap_count = _read_u8(r)
    tex.tex_code_type = _read_u8(r)
    tex.dxt_compression = _read_u8(r)
    tex._xbox_texelDataSize = _read_u32(r)

    # Palette
    if tex.raster_format & RASTER_PAL8:
        pal_size = 256
    elif tex.raster_format & RASTER_PAL4:
        pal_size = 32
    else:
        pal_size = 0

    for _ in range(pal_size):
        b, g, ra, a = struct.unpack("<BBBB", r.read(4))  # Xbox = BGRA
        tex.palette.append(PaletteEntry(ra, g, b, a))

    # Mipmaps (sizes computed, not stored)
    w, h = tex.width, tex.height
    for i in range(tex.mipmap_count):
        if i > 0:
            w = max(w // 2, 1)
            h = max(h // 2, 1)
            if tex.dxt_compression:
                w = max(w, 4)
                h = max(h, 4)

        data_size = w * h
        if tex.dxt_compression == 0:
            data_size *= tex.depth // 8
        elif tex.dxt_compression == 0x0C:
            data_size //= 2

        texel_data = r.read(data_size)
        if len(texel_data) < data_size:
            raise EOFError(
                f"Mipmap {i}: expected {data_size} bytes, got {len(texel_data)}"
            )

        tex.mipmaps.append(MipmapLevel(w, h, data_size, texel_data))

    # Extension
    ext_header = RWHeader.read(f)
    tex._raw_ext_stamp = ext_header.library_id_stamp
    tex.extension_data = f.read(ext_header.size) if ext_header.size > 0 else b""

    return tex


def _read_d3d_texture(f) -> NativeTexture:
    tex = NativeTexture()

    native_header = RWHeader.read(f)
    tex.version_stamp = native_header.library_id_stamp
    struct_header = RWHeader.read(f)
    struct_start = f.tell() # noqa: F841

    # Store raw struct data for byte-perfect round-trip
    tex._raw_struct_data = f.read(struct_header.size)

    # Parse fields from raw data
    r = io.BytesIO(tex._raw_struct_data)

    tex.platform_id = _read_u32(r)
    tex.filter_mode = _read_u32(r)
    tex.name = _read_fixed_string(r, 32)
    tex.mask_name = _read_fixed_string(r, 32)
    tex.raster_format = _read_u32(r)
    tex.has_alpha = 0

    fourcc = b"\x00\x00\x00\x00"
    if tex.platform_id == PLATFORM_D3D9:
        fourcc = r.read(4)
    else:
        tex.has_alpha = _read_u32(r)

    tex.width = _read_u16(r)
    tex.height = _read_u16(r)
    tex.depth = _read_u8(r)
    tex.mipmap_count = _read_u8(r)
    tex.tex_code_type = _read_u8(r)
    tex.dxt_compression = _read_u8(r)

    if tex.platform_id == PLATFORM_D3D9:
        tex.has_alpha = tex.dxt_compression & 0x1
        if tex.dxt_compression & 0x8:
            tex.dxt_compression = fourcc[3] - ord("0")
        else:
            tex.dxt_compression = 0

    # Palette
    if tex.raster_format & RASTER_PAL8:
        pal_size = 256
    elif tex.raster_format & RASTER_PAL4:
        pal_size = 16
    else:
        pal_size = 0

    for _ in range(pal_size):
        rv, g, b, a = struct.unpack("<BBBB", r.read(4))  # D3D = RGBA
        tex.palette.append(PaletteEntry(rv, g, b, a))

    # Mipmaps (each has dataSize prefix)
    w, h = tex.width, tex.height
    for i in range(tex.mipmap_count):
        if i > 0:
            w = max(w // 2, 1)
            h = max(h // 2, 1)
            if tex.dxt_compression:
                w = max(w, 4)
                h = max(h, 4)

        data_size = _read_u32(r)
        texel_data = r.read(data_size)
        tex.mipmaps.append(MipmapLevel(w, h, data_size, texel_data))

    # Extension
    ext_header = RWHeader.read(f)
    tex._raw_ext_stamp = ext_header.library_id_stamp
    tex.extension_data = f.read(ext_header.size) if ext_header.size > 0 else b""

    return tex


def load(filepath: Union[str, Path]) -> TextureDictionary:
    """Load a TXD file from disk.

    Args:
        filepath: Path to the .txd file.

    Returns:
        Parsed TextureDictionary.
    """
    txd = TextureDictionary()

    with open(filepath, "rb") as f:
        dict_header = RWHeader.read(f)
        if dict_header.type != CHUNK_TEXDICTIONARY:
            raise ValueError(
                f"Not a TXD: expected 0x{CHUNK_TEXDICTIONARY:02X}, "
                f"got 0x{dict_header.type:02X}"
            )

        txd.version_stamp = dict_header.library_id_stamp
        _struct_header = RWHeader.read(f)
        texture_count = _read_u16(f)
        txd.device_id = _read_u16(f)

        for _ in range(texture_count):
            # Peek platform ID: skip TEXTURENATIVE header (12) + STRUCT header (12)
            pos = f.tell()
            f.seek(pos + 0x18)
            platform = _read_u32(f)
            f.seek(pos)

            if platform == PLATFORM_XBOX:
                txd.textures.append(_read_xbox_texture(f))
            elif platform in (PLATFORM_D3D8, PLATFORM_D3D9):
                txd.textures.append(_read_d3d_texture(f))
            else:
                # Skip unknown platform
                hdr = RWHeader.read(f)
                f.read(hdr.size)

        # TXD extension (optional)
        remaining = f.read(12)
        if len(remaining) == 12:
            ext_type = struct.unpack_from("<I", remaining, 0)[0]
            ext_size = struct.unpack_from("<I", remaining, 4)[0]
            if ext_type == CHUNK_EXTENSION:
                txd._txd_extension_data = f.read(ext_size) if ext_size > 0 else b""

    return txd


def _load_from_stream(f) -> TextureDictionary:
    """Internal: load TXD from an open file-like object."""
    txd = TextureDictionary()

    dict_header = RWHeader.read(f)
    if dict_header.type != CHUNK_TEXDICTIONARY:
        raise ValueError(
            f"Not a TXD: expected 0x{CHUNK_TEXDICTIONARY:02X}, "
            f"got 0x{dict_header.type:02X}"
        )

    txd.version_stamp = dict_header.library_id_stamp
    _struct_header = RWHeader.read(f)
    texture_count = _read_u16(f)
    txd.device_id = _read_u16(f)

    for _ in range(texture_count):
        pos = f.tell()
        f.seek(pos + 0x18)
        platform = _read_u32(f)
        f.seek(pos)

        if platform == PLATFORM_XBOX:
            txd.textures.append(_read_xbox_texture(f))
        elif platform in (PLATFORM_D3D8, PLATFORM_D3D9):
            txd.textures.append(_read_d3d_texture(f))
        else:
            hdr = RWHeader.read(f)
            f.read(hdr.size)

    remaining = f.read(12)
    if len(remaining) == 12:
        ext_type = struct.unpack_from("<I", remaining, 0)[0]
        ext_size = struct.unpack_from("<I", remaining, 4)[0]
        if ext_type == CHUNK_EXTENSION:
            txd._txd_extension_data = f.read(ext_size) if ext_size > 0 else b""

    return txd


def loads(data: bytes) -> TextureDictionary:
    """Load a TXD from a bytes buffer."""
    return _load_from_stream(io.BytesIO(data))


# ═══════════════════════════════════════════════════════
#  Write TXD
# ═══════════════════════════════════════════════════════


def _build_xbox_texture_data(tex: NativeTexture) -> bytes:
    """Build the inner STRUCT data for one Xbox NativeTexture."""
    buf = io.BytesIO()

    _write_u32(buf, PLATFORM_XBOX)
    _write_u32(buf, tex.filter_mode)
    _write_fixed_string(buf, tex.name, 32)
    _write_fixed_string(buf, tex.mask_name, 32)
    _write_u32(buf, tex.raster_format)
    _write_u32(buf, tex.has_alpha)
    _write_u16(buf, tex.width)
    _write_u16(buf, tex.height)
    _write_u8(buf, tex.depth)
    _write_u8(buf, tex.mipmap_count)
    _write_u8(buf, tex.tex_code_type)
    _write_u8(buf, tex.dxt_compression)
    
    total_texel_size = sum(len(mip.texels) for mip in tex.mipmaps)
    aligned_texel_size = (total_texel_size + 3) & ~3
    _write_u32(buf, aligned_texel_size)  # texelDataSize xbox field
    
    if tex.name == "melman_tissue2":
        print(f"Total texel size: {total_texel_size}, aligned to {aligned_texel_size}")

    # Palette (BGRA on Xbox)
    for p in tex.palette:
        buf.write(struct.pack("<BBBB", p.b, p.g, p.r, p.a))

    # Mipmap texel data (no size prefix on Xbox)
    for mip in tex.mipmaps:
        buf.write(mip.texels)

    # Xbox texel payload is 4-byte aligned.
    padding = aligned_texel_size - total_texel_size
    if padding:
        buf.write(b"\x00" * padding)

    return buf.getvalue()


def _build_d3d8_texture_data(tex: NativeTexture) -> bytes:
    """Build the inner STRUCT data for one D3D8 NativeTexture."""
    buf = io.BytesIO()

    _write_u32(buf, PLATFORM_D3D8)
    _write_u32(buf, tex.filter_mode)
    _write_fixed_string(buf, tex.name, 32)
    _write_fixed_string(buf, tex.mask_name, 32)
    _write_u32(buf, tex.raster_format)
    _write_u32(buf, tex.has_alpha)
    _write_u16(buf, tex.width)
    _write_u16(buf, tex.height)
    _write_u8(buf, tex.depth)
    _write_u8(buf, tex.mipmap_count)
    _write_u8(buf, tex.tex_code_type)
    _write_u8(buf, tex.dxt_compression)

    # Palette (RGBA on D3D)
    for p in tex.palette:
        buf.write(struct.pack("<BBBB", p.r, p.g, p.b, p.a))

    # Mipmap texel data (with size prefix)
    for mip in tex.mipmaps:
        _write_u32(buf, mip.data_size)
        buf.write(mip.texels)

    return buf.getvalue()


def save(txd: TextureDictionary, filepath: Union[str, Path]):
    """Write a TextureDictionary to a .txd file.

    If textures were loaded from a file, uses raw struct data for
    byte-perfect round-trips. Otherwise builds from parsed fields.

    Args:
        txd: The TextureDictionary to write.
        filepath: Output file path.
    """
    stamp = txd.version_stamp

    # Build all texture chunks first to get sizes
    tex_chunks = []
    for tex in txd.textures:
        t_stamp = tex.version_stamp

        # Use raw struct data if available (byte-perfect round-trip)
        if tex._raw_struct_data is not None:
            struct_data = tex._raw_struct_data
        elif tex.platform_id == PLATFORM_XBOX:
            struct_data = _build_xbox_texture_data(tex)
        elif tex.platform_id in (PLATFORM_D3D8, PLATFORM_D3D9):
            struct_data = _build_d3d8_texture_data(tex)
        else:
            raise ValueError(f"Unsupported platform for writing: {tex.platform_id}")

        # Wrap in STRUCT header
        struct_chunk = (
            RWHeader(CHUNK_STRUCT, len(struct_data), t_stamp).pack() + struct_data
        )

        # Extension chunk (use stored extension stamp)
        ext_data = tex.extension_data or b""
        ext_stamp = tex._raw_ext_stamp
        ext_chunk = (
            RWHeader(CHUNK_EXTENSION, len(ext_data), ext_stamp).pack() + ext_data
        )

        # TEXTURENATIVE = STRUCT + EXTENSION
        native_data = struct_chunk + ext_chunk
        native_chunk = (
            RWHeader(CHUNK_TEXTURENATIVE, len(native_data), t_stamp).pack()
            + native_data
        )

        tex_chunks.append(native_chunk)

    # TextureDictionary STRUCT (4 bytes: count + device_id)
    dict_struct_data = struct.pack("<HH", len(txd.textures), txd.device_id)
    dict_struct_chunk = (
        RWHeader(CHUNK_STRUCT, len(dict_struct_data), stamp).pack() + dict_struct_data
    )

    # Empty extension for the TXD itself (or preserved from input)
    txd_ext_data = txd._txd_extension_data or b""
    dict_ext_chunk = (
        RWHeader(CHUNK_EXTENSION, len(txd_ext_data), stamp).pack() + txd_ext_data
    )

    # Assemble inner data
    inner = dict_struct_chunk
    for tc in tex_chunks:
        inner += tc
    inner += dict_ext_chunk

    # Outer TXD header
    txd_header = RWHeader(CHUNK_TEXDICTIONARY, len(inner), stamp).pack()

    with open(filepath, "wb") as f:
        f.write(txd_header)
        f.write(inner)


def dumps(txd: TextureDictionary) -> bytes:
    """Serialize a TextureDictionary to bytes."""
    buf = io.BytesIO() # noqa: F841
    # Build in memory using same logic as save()
    stamp = txd.version_stamp

    tex_chunks = []
    for tex in txd.textures:
        t_stamp = tex.version_stamp
        if tex._raw_struct_data is not None:
            struct_data = tex._raw_struct_data
        elif tex.platform_id == PLATFORM_XBOX:
            struct_data = _build_xbox_texture_data(tex)
        elif tex.platform_id in (PLATFORM_D3D8, PLATFORM_D3D9):
            struct_data = _build_d3d8_texture_data(tex)
        else:
            raise ValueError(f"Unsupported platform: {tex.platform_id}")

        struct_chunk = (
            RWHeader(CHUNK_STRUCT, len(struct_data), t_stamp).pack() + struct_data
        )
        ext_data = tex.extension_data or b""
        ext_chunk = (
            RWHeader(CHUNK_EXTENSION, len(ext_data), tex._raw_ext_stamp).pack()
            + ext_data
        )
        native_data = struct_chunk + ext_chunk
        native_chunk = (
            RWHeader(CHUNK_TEXTURENATIVE, len(native_data), t_stamp).pack()
            + native_data
        )
        tex_chunks.append(native_chunk)

    dict_struct_data = struct.pack("<HH", len(txd.textures), txd.device_id)
    dict_struct_chunk = (
        RWHeader(CHUNK_STRUCT, len(dict_struct_data), stamp).pack() + dict_struct_data
    )
    txd_ext_data = txd._txd_extension_data or b""
    dict_ext_chunk = (
        RWHeader(CHUNK_EXTENSION, len(txd_ext_data), stamp).pack() + txd_ext_data
    )

    inner = dict_struct_chunk
    for tc in tex_chunks:
        inner += tc
    inner += dict_ext_chunk

    result = RWHeader(CHUNK_TEXDICTIONARY, len(inner), stamp).pack() + inner
    return result


def verify(filepath: Union[str, Path]) -> bool:
    """Verify a TXD round-trips correctly: load → save → compare bytes.

    Args:
        filepath: Path to original .txd file.

    Returns:
        True if round-trip produces identical bytes.
    """
    with open(filepath, "rb") as f:
        original = f.read()

    txd = loads(original)
    rebuilt = dumps(txd)

    if original == rebuilt:
        print(f"PASS: round-trip identical ({len(original)} bytes)")
        return True
    else:
        print(
            f"FAIL: original={len(original)} bytes, rebuilt={len(rebuilt)} bytes, "
            f"diff={len(original) - len(rebuilt)}"
        )
        # Find first differing byte
        for i in range(min(len(original), len(rebuilt))):
            if original[i] != rebuilt[i]:
                print(
                    f"  First difference at offset 0x{i:X}: "
                    f"original=0x{original[i]:02X}, rebuilt=0x{rebuilt[i]:02X}"
                )
                # Show context
                start = max(0, i - 8)
                end = min(len(original), i + 8)
                print(f"  Original: {original[start:end].hex(' ')}")
                end = min(len(rebuilt), i + 8)
                print(f"  Rebuilt:  {rebuilt[start:end].hex(' ')}")
                break
        return False


# ═══════════════════════════════════════════════════════
#  Create textures from RGBA data
# ═══════════════════════════════════════════════════════


def create_texture(
    name: str,
    rgba: bytes,
    width: int,
    height: int,
    mask_name: str = "",
    depth: int = 8,
    platform: int = PLATFORM_XBOX,
    generate_mipmaps: bool = True,
    dxt: int = 0,
) -> NativeTexture:
    """Create a NativeTexture from raw RGBA pixel data.

    By default creates a PAL8 (256-color palettized) Xbox texture.
    Set dxt=1 for DXT1 compression, or depth=32 for uncompressed 32-bit.

    Args:
        name: Texture name (max 31 chars).
        rgba: RGBA pixel data, length = width * height * 4.
        width: Texture width (must be power of 2).
        height: Texture height (must be power of 2).
        mask_name: Alpha mask name.
        depth: Bits per pixel (8=palettized, 16, 32).
        platform: Target platform ID.
        generate_mipmaps: Whether to generate mipmap chain.
        dxt: DXT compression level (0=none, 1=DXT1).

    Returns:
        Configured NativeTexture ready to add to a TextureDictionary.
    """
    if len(rgba) != width * height * 4:
        raise ValueError(f"RGBA data length {len(rgba)} != {width}x{height}x4")

    tex = NativeTexture()
    tex.platform_id = platform
    tex.name = name[:31]
    tex.mask_name = mask_name[:31]
    tex.width = width
    tex.height = height
    tex.depth = depth

    # Determine alpha
    has_alpha = False
    for i in range(3, len(rgba), 4):
        if rgba[i] != 255:
            has_alpha = True
            break
    tex.has_alpha = int(has_alpha)

    if dxt:
        # DXT compressed
        tex.dxt_compression = dxt
        tex.raster_format = RASTER_8888 | RASTER_MIPMAP
        tex.depth = 16  # DXT block depth

        mip_rgba = bytearray(rgba)
        w, h = width, height
        while True:
            compressed = encode_dxt1(mip_rgba, w, h)
            tex.mipmaps.append(MipmapLevel(w, h, len(compressed), compressed))
            if not generate_mipmaps or (w <= 4 and h <= 4):
                break
            mip_rgba = _downsample_rgba(mip_rgba, w, h)
            w = max(w // 2, 4)
            h = max(h // 2, 4)

    elif depth == 8:
        # Palettized PAL8
        tex.raster_format = RASTER_8888 | RASTER_PAL8 | RASTER_MIPMAP
        palette, indices = _quantize_to_palette(rgba, width, height, 256)
        tex.palette = palette

        # Swizzle indices for Xbox
        if platform == PLATFORM_XBOX:
            swizzled = swizzle(bytes(indices), width, height, bpp=1)
        else:
            swizzled = bytes(indices)

        tex.mipmaps.append(MipmapLevel(width, height, len(swizzled), bytes(swizzled)))

        if generate_mipmaps:
            mip_rgba = bytearray(rgba)
            w, h = width, height
            while w > 1 or h > 1:
                mip_rgba = _downsample_rgba(mip_rgba, w, h)
                w = max(w // 2, 1)
                h = max(h // 2, 1)
                mip_indices = _quantize_with_palette(mip_rgba, w, h, palette)
                if platform == PLATFORM_XBOX:
                    mip_swiz = swizzle(bytes(mip_indices), w, h, bpp=1)
                else:
                    mip_swiz = bytes(mip_indices)
                tex.mipmaps.append(MipmapLevel(w, h, len(mip_swiz), bytes(mip_swiz)))

    elif depth == 32:
        # Uncompressed 32-bit BGRA
        tex.raster_format = RASTER_8888 | RASTER_MIPMAP
        bgra = _rgba_to_bgra(rgba)
        if platform == PLATFORM_XBOX:
            swizzled = swizzle(bgra, width, height, bpp=4)
        else:
            swizzled = bgra
        tex.mipmaps.append(MipmapLevel(width, height, len(swizzled), bytes(swizzled)))

        if generate_mipmaps:
            mip_rgba = bytearray(rgba)
            w, h = width, height
            while w > 1 or h > 1:
                mip_rgba = _downsample_rgba(mip_rgba, w, h)
                w = max(w // 2, 1)
                h = max(h // 2, 1)
                mbgra = _rgba_to_bgra(mip_rgba)
                if platform == PLATFORM_XBOX:
                    ms = swizzle(mbgra, w, h, bpp=4)
                else:
                    ms = mbgra
                tex.mipmaps.append(MipmapLevel(w, h, len(ms), bytes(ms)))

    elif depth == 16:
        tex.raster_format = RASTER_1555 | RASTER_MIPMAP
        packed = _rgba_to_1555(rgba, width, height)
        if platform == PLATFORM_XBOX:
            swizzled = swizzle(packed, width, height, bpp=2)
        else:
            swizzled = packed
        tex.mipmaps.append(MipmapLevel(width, height, len(swizzled), bytes(swizzled)))

        if generate_mipmaps:
            mip_rgba = bytearray(rgba)
            w, h = width, height
            while w > 1 or h > 1:
                mip_rgba = _downsample_rgba(mip_rgba, w, h)
                w = max(w // 2, 1)
                h = max(h // 2, 1)
                mp = _rgba_to_1555(mip_rgba, w, h)
                if platform == PLATFORM_XBOX:
                    ms = swizzle(mp, w, h, bpp=2)
                else:
                    ms = mp
                tex.mipmaps.append(MipmapLevel(w, h, len(ms), bytes(ms)))
    else:
        raise ValueError(f"Unsupported depth: {depth}")

    tex.mipmap_count = len(tex.mipmaps)
    if not has_alpha and tex.raster_format & RASTER_8888:
        tex.raster_format = (tex.raster_format & ~RASTER_MASK) | RASTER_888

    return tex


# ═══════════════════════════════════════════════════════
#  Image processing helpers
# ═══════════════════════════════════════════════════════


def _downsample_rgba(rgba: bytes, w: int, h: int) -> bytearray:
    """Simple 2x2 box filter downsample."""
    nw = max(w // 2, 1)
    nh = max(h // 2, 1)
    out = bytearray(nw * nh * 4)
    for y in range(nh):
        for x in range(nw):
            r = g = b = a = 0
            count = 0
            for dy in range(2):
                for dx in range(2):
                    sx = min(x * 2 + dx, w - 1)
                    sy = min(y * 2 + dy, h - 1)
                    off = (sy * w + sx) * 4
                    r += rgba[off]
                    g += rgba[off + 1]
                    b += rgba[off + 2]
                    a += rgba[off + 3]
                    count += 1
            off = (y * nw + x) * 4
            out[off] = r // count
            out[off + 1] = g // count
            out[off + 2] = b // count
            out[off + 3] = a // count
    return out


def _rgba_to_bgra(rgba: bytes) -> bytes:
    out = bytearray(len(rgba))
    for i in range(0, len(rgba), 4):
        out[i] = rgba[i + 2]
        out[i + 1] = rgba[i + 1]
        out[i + 2] = rgba[i]
        out[i + 3] = rgba[i + 3]
    return bytes(out)


def _rgba_to_1555(rgba: bytes, w: int, h: int) -> bytes:
    out = bytearray(w * h * 2)
    for i in range(w * h):
        off = i * 4
        r, g, b, a = rgba[off], rgba[off + 1], rgba[off + 2], rgba[off + 3]
        pixel = (
            ((1 if a >= 128 else 0) << 15)
            | ((r * 31 // 255) << 10)
            | ((g * 31 // 255) << 5)
            | (b * 31 // 255)
        )
        struct.pack_into("<H", out, i * 2, pixel)
    return bytes(out)


def _quantize_to_palette(rgba: bytes, w: int, h: int, max_colors: int) -> tuple:
    """Simple median-cut-ish palette quantization. Returns (palette, indices)."""
    # Collect unique colors
    color_counts = {}
    pixels = []
    for i in range(w * h):
        off = i * 4
        c = (rgba[off], rgba[off + 1], rgba[off + 2], rgba[off + 3])
        pixels.append(c)
        color_counts[c] = color_counts.get(c, 0) + 1

    unique = list(color_counts.keys())

    if len(unique) <= max_colors:
        # All colors fit directly
        palette = [PaletteEntry(c[0], c[1], c[2], c[3]) for c in unique]
        # Pad to max_colors
        while len(palette) < max_colors:
            palette.append(PaletteEntry(0, 0, 0, 255))
        color_to_idx = {c: i for i, c in enumerate(unique)}
        indices = bytearray(pixels_to_idx(pixels, color_to_idx))
    else:
        # Simple uniform quantization
        palette = []
        step = max(1, round(len(unique) / max_colors))
        sorted_colors = sorted(unique, key=lambda c: c[0] * 3 + c[1] * 6 + c[2])
        for i in range(0, len(sorted_colors), step):
            if len(palette) >= max_colors:
                break
            c = sorted_colors[i]
            palette.append(PaletteEntry(c[0], c[1], c[2], c[3]))
        while len(palette) < max_colors:
            palette.append(PaletteEntry(0, 0, 0, 255))

        indices = _quantize_with_palette(rgba, w, h, palette)

    return palette, indices


def pixels_to_idx(pixels, color_to_idx) -> bytearray:
    return bytearray(color_to_idx.get(p, 0) for p in pixels)


def _quantize_with_palette(rgba: bytes, w: int, h: int, palette: list) -> bytearray:
    """Map RGBA pixels to nearest palette index."""
    pixel_count = w * h
    if pixel_count == 0:
        return bytearray()

    pal_rgba = [(p.r, p.g, p.b, p.a) for p in palette]

    # Fast path: vectorized nearest-palette lookup.
    if np is not None and pal_rgba:
        pixels = np.frombuffer(rgba, dtype=np.uint8).reshape(pixel_count, 4).astype(np.int16)
        pal = np.asarray(pal_rgba, dtype=np.int16)
        out = np.empty(pixel_count, dtype=np.uint8)

        # Chunk to avoid large temporary arrays on big textures.
        chunk_size = 16384
        pal_i32 = pal.astype(np.int32)
        for start in range(0, pixel_count, chunk_size):
            end = min(start + chunk_size, pixel_count)
            block = pixels[start:end].astype(np.int32)
            diff = block[:, None, :] - pal_i32[None, :, :]
            dist = np.sum(diff * diff, axis=2)
            out[start:end] = np.argmin(dist, axis=1).astype(np.uint8)

        return bytearray(out.tobytes())

    # Fallback path (no NumPy): exact match shortcut + nearest-color scan.
    exact_lookup = {c: i for i, c in enumerate(pal_rgba)}
    indices = bytearray(pixel_count)
    for i in range(pixel_count):
        off = i * 4
        r, g, b, a = rgba[off], rgba[off + 1], rgba[off + 2], rgba[off + 3]

        exact = exact_lookup.get((r, g, b, a))
        if exact is not None:
            indices[i] = exact
            continue

        best_idx = 0
        best_dist = float("inf")
        for pi, pc in enumerate(pal_rgba):
            dr = r - pc[0]
            dg = g - pc[1]
            db = b - pc[2]
            da = a - pc[3]
            dist = dr * dr + dg * dg + db * db + da * da
            if dist < best_dist:
                best_dist = dist
                best_idx = pi
        indices[i] = best_idx
    return indices


# ═══════════════════════════════════════════════════════
#  PNG Import / Export (Pillow)
# ═══════════════════════════════════════════════════════


def _require_pillow():
    if Image is None:
        raise ImportError(
            "Pillow is required for PNG import/export. Install it with: pip install Pillow"
        )


def export_png(tex: NativeTexture, filepath: Union[str, Path], mipmap_index: int = 0):
    """Export a texture to a PNG file using Pillow.

    Args:
        tex: Source texture.
        filepath: Output .PNG path.
        mipmap_index: Which mipmap level to export.
    """
    _require_pillow()

    mip = tex.mipmaps[mipmap_index]
    w, h = mip.width, mip.height
    rgba = decode(tex, mipmap_index)
    img = Image.frombytes("RGBA", (w, h), bytes(rgba))
    img.save(filepath, format="PNG")

def import_png(
    filepath: Union[str, Path],
    name: str = "",
    platform: int = PLATFORM_XBOX,
    depth: int = 8,
) -> NativeTexture:
    """Import a PNG file as a NativeTexture using Pillow.

    Args:
        filepath: Path to .png file.
        name: Texture name (defaults to filename stem).
        platform: Target platform.
        depth: Output depth (8=PAL8, 16, 32).

    Returns:
        NativeTexture ready to add to a TextureDictionary.
    """
    _require_pillow()

    filepath = Path(filepath)
    if not name:
        name = filepath.stem[:31]

    with Image.open(filepath) as img:
        img_rgba = img.convert("RGBA")
        width, height = img_rgba.size
        rgba = img_rgba.tobytes()

    return create_texture(
        name, bytes(rgba), width, height, depth=depth, platform=platform
    )


# ═══════════════════════════════════════════════════════
#  Batch export
# ═══════════════════════════════════════════════════════


def export_all(txd: TextureDictionary, output_dir: Union[str, Path]):
    """Export all textures in a TXD to PNG files.

    Args:
        txd: Source texture dictionary.
        output_dir: Directory to write PNGs into (created if needed).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, tex in enumerate(txd.textures):
        name = tex.name if tex.name else f"texture_{i}"
        out_path = output_dir / f"{name}.png"
        try:
            export_png(tex, out_path)
        except Exception as e:
            print(f"  Failed to export {name}: {e}")


# ═══════════════════════════════════════════════════════
#  Pretty print
# ═══════════════════════════════════════════════════════


def dump(txd: TextureDictionary) -> str:
    """Return a human-readable summary of a TextureDictionary."""
    lines = [
        "TextureDictionary {",
        f"  textureCount: {len(txd.textures)}",
        f"  deviceId:     {txd.device_id}",
        "",
    ]

    for i, tex in enumerate(txd.textures):
        pname = PLATFORM_NAMES.get(tex.platform_id, f"Unknown({tex.platform_id})")
        lines.append(f"  Texture {i} {{")
        lines.append(f'    name:           "{tex.name}"')
        lines.append(f'    maskName:       "{tex.mask_name}"')
        lines.append(f"    platform:       {pname}")
        lines.append(f"    filterMode:     0x{tex.filter_mode:04X}")
        lines.append(
            f"    rasterFormat:   0x{tex.raster_format:04X} ({tex.pixel_format_name})"
        )
        lines.append(f"    rasterFlags:    {tex.raster_flags_str}")
        lines.append(f"    dimensions:     {tex.width}x{tex.height}")
        lines.append(f"    depth:          {tex.depth}")
        lines.append(f"    mipmapCount:    {tex.mipmap_count}")
        lines.append(f"    dxtCompression: {tex.dxt_compression}")
        lines.append(f"    hasAlpha:       {bool(tex.has_alpha)}")
        lines.append(f"    paletteSize:    {len(tex.palette)}")
        for j, mip in enumerate(tex.mipmaps):
            lines.append(
                f"    mipmap {j}: {mip.width}x{mip.height} ({mip.data_size} bytes)"
            )
        lines.append("  }")

    lines.append("}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════


def _cli():
    import sys

    usage = """rwtxd.py — RenderWare TXD Library

Usage:
    python rwtxd.py info   <file.txd>                    Print TXD structure
    python rwtxd.py export <file.txd> [output_dir]       Export all textures as PNG
    python rwtxd.py import <output.txd> <png>...         Create TXD from PNG files
    python rwtxd.py round  <file.txd> <output.txd>       Read and re-write (round-trip test)
    python rwtxd.py verify <file.txd>                    Verify byte-perfect round-trip
"""

    if len(sys.argv) < 3:
        print(usage)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "info":
        txd = load(args[0])
        print(dump(txd))

    elif cmd == "export":
        txd = load(args[0])
        print(dump(txd))
        out_dir = args[1] if len(args) > 1 else Path(args[0]).stem + "_textures"
        export_all(txd, out_dir)
        print(f"\nExported {len(txd.textures)} textures to {out_dir}/")

    elif cmd == "import":
        output_path = args[0]
        png_files = args[1:]
        if not png_files:
            print("No PNG files specified")
            sys.exit(1)

        txd = TextureDictionary()
        for png_path in png_files:
            tex = import_png(png_path)
            txd.textures.append(tex)
            print(f"  Imported {tex.name} ({tex.width}x{tex.height})")

        save(txd, output_path)
        print(f"Saved {output_path} with {len(txd.textures)} textures")

    elif cmd == "round":
        txd = load(args[0])
        save(txd, args[1])
        print(f"Round-tripped {args[0]} → {args[1]}")
        print(f"  {len(txd.textures)} textures preserved")
        # Auto-verify
        verify(args[0])

    elif cmd == "verify":
        verify(args[0])

    else:
        print(f"Unknown command: {cmd}")
        print(usage)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
