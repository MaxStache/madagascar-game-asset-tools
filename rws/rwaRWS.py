"""
rwaRWS.py — RenderWare Audio Stream (.RWS) Library
========================================================

Read, write, decode, and encode Renderware Audio RWS files.
Uses Pillow for PNG import/export.

Usage:
    import rwaRWS

    # Read
    rws = rwaRWS.load("file.rws")
    for stream in rwaRWS.stream:
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
from parser import Parser

__version__ = "1.0.0"


# ═══════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════


class CodecUUID(Enum):
    PCM16 = 0xD01BD217  # {D01BD217-3587-4EED-B9D9-B8E86EA9B995} PCM Signed 16-bit
    PSXADPCM = 0xD9EA9798  # {D9EA9798-BBBC-447B-96B2-654759102E16} PSX-ADPCM
    DSPADPCM = 0xF86215B0  # {F86215B0-31D5-4C29-BD37-CDBF9BD10C53} DSP-ADPCM (GCN/Wii)
    XBOXIMA = 0x632FA22B  # {632FA22B-11DD-458F-AA27-A5C346E9790E} Xbox IMA ADPCM
    IMAADPCM = 0xEF386593  # {EF386593-B611-432D-957F-A71ADE44227A} IMA ADPCM (PC)
    FLOAT = 0xDA1E4382  # {DA1E4382-2C99-4C61-AD99-7F364B211537} Float
    WMA = 0x3F1D8147  # {3F1D8147-B7C4-41E6-A69B-3CC0025B33C7} WMA
    MP3 = 0xBACFB36E  # {BACFB36E-529D-4692-BF53-324256B0734F} MP3
    MP2 = 0x34D09A54  # {34D09A54-57D3-409E-A6AD-2BC845AEC339} MP2
    MP1 = 0x04C15BA7  # {04C15BA7-F907-40AB-A49F-EEFEF8C4D296} MP1
    AC3 = 0xA30DB390  # {A30DB390-58A9-43C4-B9D2-55D84D3AE754} AC3
    
def read_codec_uuid(parser: Parser):
    value = parser.readUint32()
    return CodecUUID._value2member_map_.get(value, value)


# ═══════════════════════════════════════════════════════
#  Data Structures
# ═══════════════════════════════════════════════════════


@dataclass
class RWHeader:
    type: int = 0
    size: int = 0
    library_id_stamp: int = None

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



# ═══════════════════════════════════════════════════════
#  Binary I/O helpers
# ═══════════════════════════════════════════════════════



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


def _write_header(f, chunk_type: int, size: int, stamp: int = None):
    f.write(struct.pack("<III", chunk_type, size, stamp))


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
    buf = io.BytesIO()  # noqa: F841
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
