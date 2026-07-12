from enum import Enum
import io
from dataclasses import dataclass, field
from pathlib import Path
import struct
from typing import Union

from formats.lib.writer import _write_u8, _write_u32, _write_u16, _write_fixedString
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from formats.sections.EXTENSION_0003 import RW_Extension

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import numpy as np
except ImportError:
    np = None


def _require_pillow():
    if Image is None:
        raise ImportError(
            "Pillow is required for PNG import/export. Install it with: pip install Pillow"
        )


class RW_TextureNative_PlatformId(Enum):
    OGL = 2
    PS2 = 4
    XBOX = 5
    D3D8 = 8
    D3D9 = 9


class RW_TextureNative_FilterMode(Enum):
    NONE = 0x00
    NEAREST = 0x01
    LINEAR = 0x02
    MIP_NEAREST = 0x03
    MIP_LINEAR = 0x04
    LINEAR_MIP_NEAREST = 0x05
    LINEAR_MIP_LINEAR = 0x06


class RW_TextureNative_AddressingMode(Enum):
    NONE = 0x00
    WRAP = 0x01
    MIRROR = 0x02
    CLAMP = 0x03


class RWTextureFormat(Enum):
    DEFAULT = 0x0000
    FORMAT_1555 = 0x0100  # 1 bit alpha, RGB 5 bits each
    FORMAT_565 = 0x0200  # RGB 565
    FORMAT_4444 = 0x0300  # RGBA 4444
    FORMAT_LUM8 = 0x0400  # grayscale
    FORMAT_8888 = 0x0500  # RGBA 8888
    FORMAT_888 = 0x0600  # RGB 888
    FORMAT_555 = 0x0A00  # RGB 555


@dataclass
class RWTextureRasterFormat:
    format: RWTextureFormat = RWTextureFormat.DEFAULT

    autoMipmap: bool = False  # 0x1000 — RW generates mipmaps
    pal8: bool = False  # 0x2000 — 256 color palette
    pal4: bool = False  # 0x4000 — 16 color palette
    mipmap: bool = False  # 0x8000 — mipmaps included

    @staticmethod
    def decode(value: int) -> "RWTextureRasterFormat":
        f = RWTextureRasterFormat()

        f.format = RWTextureFormat(value & 0x0F00)

        f.autoMipmap = bool(value & 0x1000)
        f.pal8 = bool(value & 0x2000)
        f.pal4 = bool(value & 0x4000)
        f.mipmap = bool(value & 0x8000)

        return f

    def encode(self) -> int:
        v = self.format.value

        if self.autoMipmap:
            v |= 0x1000
        if self.pal8:
            v |= 0x2000
        if self.pal4:
            v |= 0x4000
        if self.mipmap:
            v |= 0x8000

        return v


@dataclass
class MipmapLevel:
    width: int = 0
    height: int = 0
    data_size: int = 0
    texels: bytes = b""


@dataclass
class PaletteEntry:
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255


@dataclass
class RW_TextureNative_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    platform_id: RW_TextureNative_PlatformId = field(
        default=RW_TextureNative_PlatformId.XBOX
    )

    filter_mode: RW_TextureNative_FilterMode = field(
        default=RW_TextureNative_FilterMode.NONE
    )

    addressing_modes: tuple[RW_TextureNative_AddressingMode] = field(
        default=(
            RW_TextureNative_AddressingMode.NONE,
            RW_TextureNative_AddressingMode.NONE,
        )
    )

    name: str = field(default="")
    mask_name: str = field(default="")

    raster_format: RWTextureRasterFormat = field(
        default_factory=lambda: RWTextureRasterFormat(RWTextureFormat.DEFAULT)
    )

    has_alpha: bool = field(default=False)

    width: int = field(default=0)
    height: int = field(default=0)

    bitdeph: int = field(default=0)
    mipmap_count: int = field(default=0)
    tex_code_type: int = field(default=0)
    dxt_compression: int = field(default=0)

    xbox_texel_data_size: int = field(default=0)

    palette: list = field(default_factory=list)
    mipmaps: list[MipmapLevel] = field(default_factory=list)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_TextureNative_Struct":
        texnative_s = RW_TextureNative_Struct()
        texnative_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texnative_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_TextureNative_Struct chunk type",
        )

        # Struct body spans [offset, offset + header.size); mipmap/palette reads
        # must stay inside it so we never bleed into the following EXTENSION chunk.
        struct_end = parser.offset + texnative_s.header.size

        texnative_s.platform_id = RW_TextureNative_PlatformId(parser.readUint32())

        if texnative_s.platform_id == RW_TextureNative_PlatformId.XBOX:
            texnative_s._read_xbox(parser, struct_end)
        elif texnative_s.platform_id in (
            RW_TextureNative_PlatformId.D3D8,
            RW_TextureNative_PlatformId.D3D9,
        ):
            raise NotImplementedError(
                "Direct3D 8/9 texture parsing not implemented yet"
            )
        else:
            raise NotImplementedError(
                f"Texture parsing for platform {texnative_s.platform_id} not implemented yet"
            )

        return texnative_s

    def _read_xbox(
        self: "RW_TextureNative_Struct", parser: Parser, struct_end: int = None
    ):
        # Read Xbox-specific texture data
        self.filter_mode = RW_TextureNative_FilterMode(parser.readUint8())

        # -- adressing_modes --
        adressing_modes = parser.readUint8()
        adressing_mode_u = RW_TextureNative_AddressingMode(adressing_modes & 0x0F)
        adressing_mode_v = RW_TextureNative_AddressingMode(
            (adressing_modes >> 4) & 0x0F
        )
        self.addressing_modes = (adressing_mode_u, adressing_mode_v)

        _padding = parser.readUint16()  # Padding, should be 0
        # ----

        self.name = parser.readString(32).replace("\00", "")
        self.mask_name = parser.readString(32).replace("\00", "")

        self.raster_format = RWTextureRasterFormat.decode(parser.readUint32())

        self.has_alpha = bool(parser.readUint32())

        self.width = parser.readUint16()
        self.height = parser.readUint16()

        self.bitdeph = parser.readUint8()
        self.mipmap_count = parser.readUint8()
        self.tex_code_type = parser.readUint8()
        self.dxt_compression = parser.readUint8()

        self._xbox_texel_data_size = (
            parser.readUint32()
        )  # total size of all mipmap texels

        # Palette
        if self.raster_format.pal8:
            pal_size = 256
        elif self.raster_format.pal4:
            pal_size = 32
        else:
            pal_size = 0

        for _ in range(pal_size):
            b, g, ra, a = struct.unpack("<BBBB", parser.read(4))  # Xbox = BGRA
            self.palette.append(PaletteEntry(ra, g, b, a))

        mipmap_data_size = 0

        for mip_level in range(self.mipmap_count):
            data_size, w, h = self._xbox_calc_mipmap(mip_level)
            mipmap_data_size += data_size

            self.mipmaps.append(MipmapLevel(w, h, data_size, parser.read(data_size)))

        padding = ((mipmap_data_size + 3) & ~3) - mipmap_data_size
        parser.skip(padding)

    def _xbox_calc_mipmap(self, mip_level: int) -> int:
        """Return the byte size of a specific mip level."""

        if mip_level < 0 or mip_level >= self.mipmap_count:
            raise ValueError(f"Invalid mip level: {mip_level}")

        w, h = self.width, self.height

        # Compute dimensions for the requested mip
        for _ in range(mip_level):
            w = max(w // 2, 1)
            h = max(h // 2, 1)

            if self.dxt_compression:
                # DXT textures are stored in at least one 4x4 block.
                w = max(w, 4)
                h = max(h, 4)

        data_size = w * h

        if self.dxt_compression == 0:
            data_size *= self.bitdeph // 8
        elif self.dxt_compression == 0x0C:
            # DXT1: 4 bits per pixel
            data_size //= 2

        # Final mip is padded to a 4-byte boundary
        # if mip_level == self.mipmap_count - 1:
        #    data_size = (data_size + 3) & ~3

        return data_size, w, h

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        # write for xbox platform (currently)

        if this.platform_id != RW_TextureNative_PlatformId.XBOX:
            raise NotImplementedError(
                f"Writing textures for platform {this.platform_id} not implemented yet"
            )

        _write_u32(buf, this.platform_id.value)

        _write_u8(buf, this.filter_mode.value)

        addressing_modes = (this.addressing_modes[0].value & 0x0F) | (
            (this.addressing_modes[1].value & 0x0F) << 4
        )
        _write_u8(
            buf, addressing_modes
        )

        _write_u16(buf, 0)  # padding

        _write_fixedString(buf, this.name, 32)
        _write_fixedString(buf, this.mask_name, 32)

        _write_u32(buf, this.raster_format.encode())
        _write_u32(buf, int(this.has_alpha))

        _write_u16(buf, this.width)
        _write_u16(buf, this.height)

        _write_u8(buf, this.bitdeph)
        _write_u8(buf, this.mipmap_count)
        _write_u8(buf, this.tex_code_type)
        _write_u8(buf, this.dxt_compression)

        mipmap_data_size = 0
        for mip_level in range(this.mipmap_count):
            data_size, _, _ = this._xbox_calc_mipmap(mip_level)
            mipmap_data_size += data_size

        _write_u32(buf, (mipmap_data_size + 3) & ~3)  # pad to 4b aligned

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_TextureNative(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_TextureNative_Struct = field(default_factory=RW_TextureNative_Struct)

    extension: RW_Extension = field(default_factory=RW_Extension)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_TextureNative":
        texnative = RW_TextureNative()
        texnative.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texnative.header,
            RWSectionType.rwID_TEXTURENATIVE.value,
            "RW_TextureNative chunk type",
        )

        texnative.struct = RW_TextureNative_Struct.read(parser, parent=texnative)

        texnative.extension = RW_Extension.read(parser, parent=texnative)

        return texnative

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        this.struct.write(buf, stamp, parent=this)

        this.extension.write(buf, stamp, parent=this)

        rw_header = RWHeader(
            type=RWSectionType.rwID_TEXTURENATIVE.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    def decode(this, mipmap_index: int = 0) -> bytes:
        """Decode a NativeTexture mipmap level to raw RGBA bytes.

        Args:
            tex: The texture to decode.
            mipmap_index: Which mipmap level (0 = full resolution).

        Returns:
            RGBA pixel data as bytes, length = width * height * 4.
        """
        mip = this.struct.mipmaps[mipmap_index]
        w, h = mip.width, mip.height

        if this.struct.palette and this.struct.dxt_compression == 0:
            indices = unswizzle(mip.texels, w, h, bpp=1)
            rgba = bytearray(w * h * 4)
            for i, idx in enumerate(indices):
                if idx < len(this.struct.palette):
                    p = this.struct.palette[idx]
                    rgba[i * 4 : i * 4 + 4] = bytes((p.r, p.g, p.b, p.a))
            return bytes(rgba)

        elif this.struct.dxt_compression == 0 and not this.struct.palette:
            if this.struct.depth == 32:
                raw = unswizzle(mip.texels, w, h, bpp=4)
                rgba = bytearray(w * h * 4)
                for i in range(w * h):
                    off = i * 4
                    rgba[off] = raw[off + 2]  # R ← B
                    rgba[off + 1] = raw[off + 1]  # G
                    rgba[off + 2] = raw[off]  # B ← R
                    rgba[off + 3] = raw[off + 3]  # A
                return bytes(rgba)

            elif this.struct.depth == 16:
                raw = unswizzle(mip.texels, w, h, bpp=2)
                rgba = bytearray(w * h * 4)
                fmt = this.struct.raster_format.format
                for i in range(w * h):
                    pixel = struct.unpack_from("<H", raw, i * 2)[0]
                    if fmt == RWTextureFormat.FORMAT_1555:
                        a = 255 if (pixel >> 15) & 1 else 0
                        r = ((pixel >> 10) & 0x1F) * 255 // 31
                        g = ((pixel >> 5) & 0x1F) * 255 // 31
                        b = (pixel & 0x1F) * 255 // 31
                    elif fmt == RWTextureFormat.FORMAT_565:
                        r = ((pixel >> 11) & 0x1F) * 255 // 31
                        g = ((pixel >> 5) & 0x3F) * 255 // 63
                        b = (pixel & 0x1F) * 255 // 31
                        a = 255
                    elif fmt == RWTextureFormat.FORMAT_4444:
                        a = ((pixel >> 12) & 0xF) * 255 // 15
                        r = ((pixel >> 8) & 0xF) * 255 // 15
                        g = ((pixel >> 4) & 0xF) * 255 // 15
                        b = (pixel & 0xF) * 255 // 15
                    else:
                        r = g = b = a = 0
                    rgba[i * 4 : i * 4 + 4] = bytes((r, g, b, a))
                return bytes(rgba)

        elif this.struct.dxt_compression in (1, 0x0C):
            return decode_dxt1(mip.texels, w, h)

        elif this.struct.dxt_compression == 3:
            return decode_dxt3(mip.texels, w, h)

        elif this.struct.dxt_compression == 5:
            return decode_dxt5(mip.texels, w, h)

        raise ValueError(
            f"Unsupported format: depth={this.struct.depth}, "
            f"dxt={this.struct.dxt_compression}, palette_length={len(this.struct.palette)}"
        )


    def export_png(this, filepath: Union[str, Path], mipmap_index: int = 0):
        """Export a texture to a PNG file using Pillow.

        Args:
            filepath: Output .PNG path.
            mipmap_index: Which mipmap level to export.
        """
        _require_pillow()

        mip = this.struct.mipmaps[mipmap_index]
        w, h = mip.width, mip.height
        rgba = this.decode(mipmap_index)
        img = Image.frombytes("RGBA", (w, h), bytes(rgba))
        img.save(filepath, format="PNG")

    def from_png(
        filepath: Union[str, Path],
        name: str = "",
        platform: int = RW_TextureNative_PlatformId.XBOX,
        depth: int = 8,
    ) -> "RW_TextureNative":
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
#  Swizzle / Unswizzle (Xbox Morton Z-order)
# ═══════════════════════════════════════════════════════


def _spread_bits(v: int) -> int:
    v = v & 0x0000FFFF
    v = (v | (v << 8)) & 0x00FF00FF
    v = (v | (v << 4)) & 0x0F0F0F0F
    v = (v | (v << 2)) & 0x33333333
    v = (v | (v << 1)) & 0x55555555
    return v


def _morton_encode(x: int, y: int) -> int:
    return _spread_bits(x) | (_spread_bits(y) << 1)


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
#  Create textures from RGBA data
# ═══════════════════════════════════════════════════════


def create_texture(
    name: str,
    rgba: bytes,
    width: int,
    height: int,
    mask_name: str = "",
    depth: int = 8,
    platform: RW_TextureNative_PlatformId = RW_TextureNative_PlatformId.XBOX,
    generate_mipmaps: bool = True,
    dxt: int = 0,
) -> RW_TextureNative:
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

    tex = RW_TextureNative()
    tex.struct.platform_id = platform
    tex.struct.name = name[:31]
    tex.struct.mask_name = mask_name[:31]
    tex.struct.width = width
    tex.struct.height = height
    tex.struct.bitdeph = depth

    # Determine alpha
    has_alpha = False
    for i in range(3, len(rgba), 4):
        if rgba[i] != 255:
            has_alpha = True
            break
    tex.struct.has_alpha = int(has_alpha)

    if dxt:
        # DXT compressed
        tex.dxt_compression = dxt
        tex.raster_format = RWTextureRasterFormat(
            RWTextureFormat.FORMAT_8888, False, False, False, True
        )
        tex.depth = 16  # DXT block depth

        mip_rgba = bytearray(rgba)
        w, h = width, height
        while True:
            compressed = encode_dxt1(mip_rgba, w, h)
            tex.struct.mipmaps.append(MipmapLevel(w, h, len(compressed), compressed))
            if not generate_mipmaps or (w <= 4 and h <= 4):
                break
            mip_rgba = _downsample_rgba(mip_rgba, w, h)
            w = max(w // 2, 4)
            h = max(h // 2, 4)

    elif depth == 8:
        # Palettized PAL8
        tex.raster_format = RWTextureRasterFormat(
            RWTextureFormat.FORMAT_8888, False, True, False, True
        )
        palette, indices = _quantize_to_palette(rgba, width, height, 256)
        tex.struct.palette = palette

        # Swizzle indices for Xbox
        if platform == RW_TextureNative_PlatformId.XBOX:
            swizzled = swizzle(bytes(indices), width, height, bpp=1)
        else:
            swizzled = bytes(indices)

        tex.struct.mipmaps.append(
            MipmapLevel(width, height, len(swizzled), bytes(swizzled))
        )

        if generate_mipmaps:
            mip_rgba = bytearray(rgba)
            w, h = width, height
            while w > 1 or h > 1:
                mip_rgba = _downsample_rgba(mip_rgba, w, h)
                w = max(w // 2, 1)
                h = max(h // 2, 1)
                mip_indices = _quantize_with_palette(mip_rgba, w, h, palette)
                if platform == RW_TextureNative_PlatformId.XBOX:
                    mip_swiz = swizzle(bytes(mip_indices), w, h, bpp=1)
                else:
                    mip_swiz = bytes(mip_indices)
                tex.struct.mipmaps.append(
                    MipmapLevel(w, h, len(mip_swiz), bytes(mip_swiz))
                )

    elif depth == 32:
        # Uncompressed 32-bit BGRA
        tex.struct.raster_format = RWTextureRasterFormat(
            RWTextureFormat.FORMAT_8888, False, False, False, True
        )
        bgra = _rgba_to_bgra(rgba)
        if platform == RW_TextureNative_PlatformId.XBOX:
            swizzled = swizzle(bgra, width, height, bpp=4)
        else:
            swizzled = bgra
        tex.struct.mipmaps.append(
            MipmapLevel(width, height, len(swizzled), bytes(swizzled))
        )

        if generate_mipmaps:
            mip_rgba = bytearray(rgba)
            w, h = width, height
            while w > 1 or h > 1:
                mip_rgba = _downsample_rgba(mip_rgba, w, h)
                w = max(w // 2, 1)
                h = max(h // 2, 1)
                mbgra = _rgba_to_bgra(mip_rgba)
                if platform == RW_TextureNative_PlatformId.XBOX:
                    ms = swizzle(mbgra, w, h, bpp=4)
                else:
                    ms = mbgra
                tex.struct.mipmaps.append(MipmapLevel(w, h, len(ms), bytes(ms)))

    elif depth == 16:
        tex.struct.raster_format = RWTextureRasterFormat(
            RWTextureFormat.FORMAT_1555, False, False, False, True
        )
        packed = _rgba_to_1555(rgba, width, height)
        if platform == RW_TextureNative_PlatformId.XBOX:
            swizzled = swizzle(packed, width, height, bpp=2)
        else:
            swizzled = packed
        tex.struct.mipmaps.append(
            MipmapLevel(width, height, len(swizzled), bytes(swizzled))
        )

        if generate_mipmaps:
            mip_rgba = bytearray(rgba)
            w, h = width, height
            while w > 1 or h > 1:
                mip_rgba = _downsample_rgba(mip_rgba, w, h)
                w = max(w // 2, 1)
                h = max(h // 2, 1)
                mp = _rgba_to_1555(mip_rgba, w, h)
                if platform == RW_TextureNative_PlatformId.XBOX:
                    ms = swizzle(mp, w, h, bpp=2)
                else:
                    ms = mp
                tex.struct.mipmaps.append(MipmapLevel(w, h, len(ms), bytes(ms)))
    else:
        raise ValueError(f"Unsupported depth: {depth}")

    tex.struct.mipmap_count = len(tex.struct.mipmaps)
    if not has_alpha and tex.struct.raster_format.format == RWTextureFormat.FORMAT_8888:
        tex.struct.raster_format = RWTextureRasterFormat(
            RWTextureFormat.FORMAT_888, False, False, False, True
        )
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
        pixels = (
            np.frombuffer(rgba, dtype=np.uint8).reshape(pixel_count, 4).astype(np.int16)
        )
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
