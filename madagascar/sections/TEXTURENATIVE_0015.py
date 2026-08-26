from enum import Enum
import io
from dataclasses import dataclass, field
from pathlib import Path
import struct
from typing import BinaryIO, override

from madagascar.lib.writer import write_u8, write_u32, write_u16, write_fixedString
from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from madagascar.sections.EXTENSION_0003 import RW_Extension
from madagascar.sections.STRING_0002 import RW_String


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
    PS2_FOURCC = 0x00325350  # ASCII "PS2\0", used by RW3 instead of the numeric id
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


from dataclasses import dataclass


@dataclass
class GSTex0:
    tbp0: int = 0
    tbw: int = 0
    psm: int = 0
    tw: int = 0
    th: int = 0
    tcc: int = 0
    tfx: int = 0
    cbp: int = 0
    cpsm: int = 0
    csm: int = 0
    csa: int = 0
    cld: int = 0

    @staticmethod
    def decode(value: int) -> "GSTex0":
        return GSTex0(
            tbp0=value & 0x3FFF,
            tbw=(value >> 14) & 0x3F,
            psm=(value >> 20) & 0x3F,
            tw=(value >> 26) & 0xF,
            th=(value >> 30) & 0xF,
            tcc=(value >> 34) & 0x1,
            tfx=(value >> 35) & 0x3,
            cbp=(value >> 37) & 0x3FFF,
            cpsm=(value >> 51) & 0xF,
            csm=(value >> 55) & 0x1,
            csa=(value >> 56) & 0x1F,
            cld=(value >> 61) & 0x7,
        )

    def encode(self) -> int:
        return (
            (self.tbp0 & 0x3FFF)
            | ((self.tbw & 0x3F) << 14)
            | ((self.psm & 0x3F) << 20)
            | ((self.tw & 0xF) << 26)
            | ((self.th & 0xF) << 30)
            | ((self.tcc & 0x1) << 34)
            | ((self.tfx & 0x3) << 35)
            | ((self.cbp & 0x3FFF) << 37)
            | ((self.cpsm & 0xF) << 51)
            | ((self.csm & 0x1) << 55)
            | ((self.csa & 0x1F) << 56)
            | ((self.cld & 0x7) << 61)
        )


@dataclass
class GSTex1:
    lcm: int = 0
    mxl: int = 0
    mmag: int = 0
    mmin: int = 0
    mtba: int = 0
    l: int = 0
    k: int = 0

    @staticmethod
    def decode(value: int) -> "GSTex1":
        return GSTex1(
            lcm=value & 0x1,
            mxl=(value >> 2) & 0x7,
            mmag=(value >> 5) & 0x1,
            mmin=(value >> 6) & 0x7,
            mtba=(value >> 9) & 0x1,
            l=(value >> 19) & 0x3,
            k=(value >> 32) & 0xFFF,
        )

    def encode(self) -> int:
        return (
            (self.lcm & 0x1)
            | ((self.mxl & 0x7) << 2)
            | ((self.mmag & 0x1) << 5)
            | ((self.mmin & 0x7) << 6)
            | ((self.mtba & 0x1) << 9)
            | ((self.l & 0x3) << 19)
            | ((self.k & 0xFFF) << 32)
        )

    @property
    def mipmap_count(self) -> int:
        return self.mxl + 1


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

    addressing_modes: tuple[
        RW_TextureNative_AddressingMode, RW_TextureNative_AddressingMode
    ] = field(
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

    texel_data_size: int = field(default=0)

    # False when the struct chunk ended after the fixed fields, carrying no
    # palette or texels. Every raster the game ships has them, so this means
    # the file was damaged by a tool that wrote the header without the data.
    has_texel_data: bool = field(default=True)

    pallette_data_size: int = field(default=0)

    palette: list[PaletteEntry] = field(default_factory=list)
    mipmaps: list[MipmapLevel] = field(default_factory=list)

    _ps2_tex0: GSTex0 = field(default_factory=GSTex0)
    _ps2_tex1: GSTex1 = field(default_factory=GSTex1)
    _ps2_miptbp1: int = field(default=0)
    _ps2_miptbp2: int = field(default=0)

    _ps2_gpuDataAlignedSize: int = field(default=0)
    skyMipmapValue: int = field(default=0)

    @classmethod
    @override
    def read(
        cls, parser: Parser, parent: RW_Section | None = None
    ) -> "RW_TextureNative_Struct":
        texnative_s = cls()
        texnative_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texnative_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_TextureNative_Struct chunk type",
        )
        print(texnative_s.header)

        # The chunk's declared size is authoritative for where this section
        # ends. Every raster in a well formed dictionary carries its palette
        # and texels, but a file written back by a tool that dropped them
        # stops right after the fixed fields, and reading on would consume the
        # following chunks.
        struct_end = parser.tell() + texnative_s.header.size

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
        elif texnative_s.platform_id in (
            RW_TextureNative_PlatformId.PS2,
            RW_TextureNative_PlatformId.PS2_FOURCC,
        ):
            texnative_s._read_PS2(parser)
        else:
            raise NotImplementedError(
                f"Texture parsing for platform {texnative_s.platform_id} not implemented yet"
            )

        return texnative_s

    def _read_PS2(self, parser: Parser):
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

        self.name = RW_String.read(parser).content  # name
        self.mask_name = RW_String.read(parser).content  # mask_name

        # Outer struct wrapping the raster format header, the palette and the
        # texel data. Its declared size is authoritative for where this whole
        # section ends, so we seek to it at the end instead of recomputing
        # padding by hand.
        rfmt_h = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            rfmt_h,
            RWSectionType.rwID_STRUCT.value,
            "RW_TextureNative_Struct raster format chunk type",
        )
        rfmt_end = parser.tell() + rfmt_h.size

        # Raster format fields themselves are wrapped in a *second*, nested
        # struct chunk (64 bytes of payload: width/height/depth/rasterformat,
        # the GS tex0/tex1/miptbp registers, and the size fields below).
        raster_h = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            raster_h,
            RWSectionType.rwID_STRUCT.value,
            "RW_TextureNative_Struct nested raster format chunk type",
        )

        self.width = parser.readUint32()
        self.height = parser.readUint32()
        self.bitdeph = parser.readUint32()
        self.raster_format = RWTextureRasterFormat.decode(parser.readUint32())

        # See PS2 GS_Users_Manual.pdf
        self._ps2_tex0 = GSTex0.decode(parser.readUint64())
        self._ps2_tex1 = GSTex1.decode(parser.readUint64())
        self._ps2_miptbp1 = parser.readUint64()
        self._ps2_miptbp2 = parser.readUint64()

        self.texel_data_size = parser.readUint32()  # stream size of the mipmap data
        self.pallette_data_size = (
            parser.readUint32()
        )  # stream size of the palette data (zero if no palette)
        self._ps2_gpuDataAlignedSize = (
            parser.readUint32()
        )  # memory span of the texture mipmap data on the GS (aligned to pages/2048)

        self.skyMipmapValue = parser.readUint32()

        # Texel (mipmap) data is stored before the palette on disk, each as a
        # sequence of GS transfer blocks (one per mipmap level for the texels,
        # one for the palette). The pixel region additionally opens with a
        # 12-byte pointer preamble which texel_data_size does not account for,
        # so it has to be consumed separately or the palette read starts 12
        # bytes early and loses its last 3 entries.
        mip_count = 1

        if self.raster_format.mipmap:
            mip_count = self._ps2_tex1.mipmap_count

        parser.read(_PS2_PIXEL_REGION_PREAMBLE_SIZE)
        texel_region = parser.read(self.texel_data_size)

        for mip_level, texels in enumerate(
            _ps2_iter_transfer_blocks(texel_region, mip_count)
        ):
            _, w, h = self._ps2_calc_mipmap(mip_level)
            self.mipmaps.append(MipmapLevel(w, h, len(texels), texels))

        # Palette
        palette_blob = b"".join(
            _ps2_iter_transfer_blocks(parser.read(self.pallette_data_size), 1)
        )
        pal_entries = len(palette_blob) // 4

        for i in range(pal_entries):
            r, g, b, a = struct.unpack_from("<BBBB", palette_blob, i * 4)
            self.palette.append(PaletteEntry(r, g, b, a))

        self.palette = ps2_unswizzle_clut(self.palette)

        # The PS2 GS mipmap chain isn't always packed to a plain w*h*bpp/8 sum
        # per level (page/block alignment on the GS side), so rely on the
        # outer struct's declared size to land exactly on the next chunk
        # rather than recomputing the trailing padding ourselves.
        parser.seek(rfmt_end)


    def _ps2_calc_mipmap(self, mip_level: int) -> tuple[int, int, int]:
        """Return (data_size, width, height) for a PS2 mip level."""

        if mip_level < 0:
            raise ValueError(f"Invalid mip level: {mip_level}")

        w = self.width
        h = self.height

        for _ in range(mip_level):
            w = max(w // 2, 1)
            h = max(h // 2, 1)

        psm = self._ps2_tex0.psm

        # GS pixel storage mode
        match psm:
            case 0x00:  # PSMCT32
                bpp = 32
            case 0x02:  # PSMCT16
                bpp = 16
            case 0x0A:  # PSMCT16S
                bpp = 16
            case 0x13:  # PSMT8
                bpp = 8
            case 0x14:  # PSMT4
                bpp = 4
            case _:
                raise NotImplementedError(f"Unsupported PS2 PSM 0x{psm:02X}")

        data_size = (w * h * bpp) // 8

        return data_size, w, h

    def _read_xbox(self: "RW_TextureNative_Struct", parser: Parser, struct_end: int):
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

        self.texel_data_size = parser.readUint32()  # total size of all mipmap texels

        if parser.tell() >= struct_end:
            # texel_data_size is declared but the bytes are not there. Flag it
            # and stop, rather than reading into the next chunk.
            self.has_texel_data = False
            return

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

        texel_data_size = 0

        for mip_level in range(self.mipmap_count):
            data_size, w, h = self._xbox_calc_mipmap(mip_level)
            texel_data_size += data_size

            self.mipmaps.append(MipmapLevel(w, h, data_size, parser.read(data_size)))

        padding = ((texel_data_size + 3) & ~3) - texel_data_size # pad to 4b
        parser.skip(padding)

    def _xbox_calc_mipmap(self, mip_level: int) -> tuple[int, int, int]:
        """Return the byte size of a specific mip level."""

        if mip_level < 0:  # or mip_level >= self.mipmap_count:
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

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        # write for xbox platform (currently)

        if self.platform_id != RW_TextureNative_PlatformId.XBOX:
            raise NotImplementedError(
                f"Writing textures for platform {self.platform_id} not implemented yet"
            )

        write_u32(buf, self.platform_id.value)

        write_u8(buf, self.filter_mode.value)

        addressing_modes = (self.addressing_modes[0].value & 0x0F) | (
            (self.addressing_modes[1].value & 0x0F) << 4
        )
        write_u8(buf, addressing_modes)

        write_u16(buf, 0)  # padding

        write_fixedString(buf, self.name, 32)
        write_fixedString(buf, self.mask_name, 32)

        write_u32(buf, self.raster_format.encode())
        write_u32(buf, int(self.has_alpha))

        write_u16(buf, self.width)
        write_u16(buf, self.height)

        write_u8(buf, self.bitdeph)
        write_u8(buf, self.mipmap_count)
        write_u8(buf, self.tex_code_type)
        write_u8(buf, self.dxt_compression)

        texel_data_size = 0
        for mip_level in range(self.mipmap_count):
            data_size, _, _ = self._xbox_calc_mipmap(mip_level)
            texel_data_size += data_size

        write_u32(buf, (texel_data_size + 3) & ~3)  # pad to 4b aligned

        # Metadata-only entries (texture folder dictionaries) declare a texel
        # size but carry no palette or texels, and the body ends here.
        if self.has_texel_data:
            for entry in self.palette:
                buf.write(struct.pack("<BBBB", entry.b, entry.g, entry.r, entry.a))

            written = 0
            for mip in self.mipmaps:
                buf.write(mip.texels)
                written += len(mip.texels)

            buf.write(b"\x00" * (((written + 3) & ~3) - written))  # pad to 4b

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

    @classmethod
    @override
    def read(
        cls, parser: Parser, parent: RW_Section | None = None
    ) -> "RW_TextureNative":
        texnative = cls()
        texnative.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texnative.header,
            RWSectionType.rwID_TEXTURENATIVE.value,
            "RW_TextureNative chunk type",
        )

        texnative.struct = RW_TextureNative_Struct.read(parser, parent=texnative)

        texnative.extension = RW_Extension.read(parser, parent=texnative)

        return texnative

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        self.struct.write(buf, stamp, parent=self)

        self.extension.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_TEXTURENATIVE.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    def decode(self, mipmap_index: int = 0) -> bytes:
        """Decode a NativeTexture mipmap level to raw RGBA bytes.

        Args:
            tex: The texture to decode.
            mipmap_index: Which mipmap level (0 = full resolution).

        Returns:
            RGBA pixel data as bytes, length = width * height * 4.
        """
        mip = self.struct.mipmaps[mipmap_index]
        w, h = mip.width, mip.height

        is_ps2 = self.struct.platform_id in (
            RW_TextureNative_PlatformId.PS2,
            RW_TextureNative_PlatformId.PS2_FOURCC,
        )

        if self.struct.palette and self.struct.dxt_compression == 0:
            if is_ps2:
                index_bpp = 4 if self.struct.raster_format.pal4 else 8
                indices = ps2_unswizzle_indices(mip.texels, w, h, bpp=index_bpp)
            else:
                indices = unswizzle(mip.texels, w, h, bpp=1)
            rgba = bytearray(w * h * 4)
            for i, idx in enumerate(indices):
                if idx < len(self.struct.palette):
                    p = self.struct.palette[idx]
                    a = min(p.a * 2, 255) if is_ps2 else p.a
                    rgba[i * 4 : i * 4 + 4] = bytes((p.r, p.g, p.b, a))
            return bytes(rgba)

        elif self.struct.dxt_compression == 0 and not self.struct.palette:
            if self.struct.bitdeph == 32:
                raw = mip.texels if is_ps2 else unswizzle(mip.texels, w, h, bpp=4)
                rgba = bytearray(w * h * 4)
                for i in range(w * h):
                    off = i * 4
                    rgba[off] = raw[off + 2]  # R ← B
                    rgba[off + 1] = raw[off + 1]  # G
                    rgba[off + 2] = raw[off]  # B ← R
                    rgba[off + 3] = raw[off + 3]  # A
                return bytes(rgba)

            elif self.struct.bitdeph == 16:
                raw = mip.texels if is_ps2 else unswizzle(mip.texels, w, h, bpp=2)
                rgba = bytearray(w * h * 4)
                fmt = self.struct.raster_format.format
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

        elif self.struct.dxt_compression in (1, 0x0C):
            return decode_dxt1(mip.texels, w, h)

        elif self.struct.dxt_compression == 3:
            return decode_dxt3(mip.texels, w, h)

        elif self.struct.dxt_compression == 5:
            return decode_dxt5(mip.texels, w, h)

        raise ValueError(
            f"Unsupported format: bitdepth={self.struct.bitdeph}, "
            + f"dxt={self.struct.dxt_compression}, palette_length={len(self.struct.palette)}"
        )

    def export_png(
        self,
        filepath: str | Path,
        mipmap_index: int = 0,
        all_mipmaps: bool = False,
    ):
        """Export a texture to a PNG file using Pillow.

        Args:
            filepath: Output .PNG path.
            mipmap_index: Which mipmap level to export. Ignored when
                all_mipmaps is set.
            all_mipmaps: Lay every mipmap level out side by side in a single
                image, largest first, top aligned.
        """
        _require_pillow()

        assert Image is not None, (
            "Pillow is required for PNG export"
        )  # Should never run actually

        if all_mipmaps:
            self._mipmap_sheet().save(filepath, format="PNG") # type: ignore
            return

        mip = self.struct.mipmaps[mipmap_index]
        w, h = mip.width, mip.height
        rgba = self.decode(mipmap_index)

        img = Image.frombytes("RGBA", (w, h), bytes(rgba))

        img.save(filepath, format="PNG")

    def _mipmap_sheet(self, gap: int = 0) -> "Image.Image": # type: ignore
        """Compose every mipmap level into one image, largest first.

        Args:
            gap: Transparent padding to leave between levels, in pixels.

        Returns:
            An RGBA image with the levels laid out left to right, top aligned.
        """
        assert Image is not None

        levels = [
            Image.frombytes(
                "RGBA", (mip.width, mip.height), bytes(self.decode(index))
            )
            for index, mip in enumerate(self.struct.mipmaps)
        ]

        # mipmaps[0] is already the full resolution level, so stream order is
        # largest to smallest.
        total_width = sum(level.width for level in levels) + gap * (len(levels) - 1)
        sheet = Image.new("RGBA", (total_width, levels[0].height), (0, 0, 0, 0))

        x = 0
        for level in levels:
            sheet.paste(level, (x, 0))
            x += level.width + gap

        return sheet

    @staticmethod
    def from_png(
        filepath: str | Path,
        name: str = "",
        platform: RW_TextureNative_PlatformId = RW_TextureNative_PlatformId.XBOX,
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

        assert Image is not None, (
            "Pillow is required for PNG import"
        )  # Should never run actually
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
#  PS2 GS transfer blocks
# ═══════════════════════════════════════════════════════

# Every PS2 texel/palette payload is preceded by a 0x50 byte transfer
# descriptor: a PACKED GIFtag announcing three A+D register writes
# (TRXPOS/TRXREG/TRXDIR, 16 bytes each: data qword then address qword),
# followed by an IMAGE mode GIFtag whose NLOOP counts the payload that comes
# after it in 16 byte quadwords.
_PS2_TRANSFER_DESCRIPTOR_SIZE = 0x50
_PS2_IMAGE_GIFTAG_OFFSET = 0x40

# The pixel region opens with a 12 byte pointer preamble that sits outside the
# declared texel_data_size.
_PS2_PIXEL_REGION_PREAMBLE_SIZE = 12


def _ps2_iter_transfer_blocks(region: bytes, max_blocks: int):
    """Yield the payload of each GS transfer block in a PS2 texel/palette region.

    Args:
        region: The raw texel or palette region, starting at a descriptor.
        max_blocks: Stop after this many blocks (one per mipmap level, or 1 for
            a palette).

    Yields:
        The payload bytes of each block, in stream order.
    """
    offset = 0

    for _ in range(max_blocks):
        if offset + _PS2_TRANSFER_DESCRIPTOR_SIZE > len(region):
            return

        image_giftag = struct.unpack_from(
            "<Q", region, offset + _PS2_IMAGE_GIFTAG_OFFSET
        )[0]
        payload_size = (image_giftag & 0x7FFF) * 16  # NLOOP quadwords

        offset += _PS2_TRANSFER_DESCRIPTOR_SIZE
        yield region[offset : offset + payload_size]
        offset += payload_size


# ═══════════════════════════════════════════════════════
#  Swizzle / Unswizzle (PS2 GS block layout)
# ═══════════════════════════════════════════════════════


def _ps2_swizzle_addr(x: int, y: int, logw: int) -> int:
    """PS2 GS PSMT4/PSMT8 block-swizzle address, per librw's `swizzle()`."""
    y1 = (y >> 1) & 1
    y2 = (y >> 2) & 1
    x ^= (y1 ^ y2) << 2
    x3 = (x >> 3) & 1
    nx = (x & 7) | ((x >> 1) & ~7)
    ny = (y & 1) | ((y >> 1) & ~1)
    n = y1 | (x3 << 1)
    return n | (nx << 2) | (ny << (logw - 1 + 2))


def ps2_unswizzle_clut(palette: list[PaletteEntry]) -> list[PaletteEntry]:
    """Reorder a PS2 PSMT8 CLUT from GS block order into linear index order.

    A 256 entry CLUT is uploaded to the GS as a 16x16 PSMCT32 block, and within
    each group of 32 entries the two middle runs of 8 end up transposed, so they
    have to be swapped back before the palette can be indexed linearly. 16 entry
    PSMT4 CLUTs are stored in order already and are returned untouched.

    Args:
        palette: Palette entries in the on-disk (GS) order.

    Returns:
        Palette entries in linear index order.
    """
    if len(palette) < 256:
        return palette

    out = list(palette)
    for base in range(0, 256, 32):
        for j in range(8):
            lo, hi = base + 8 + j, base + 16 + j
            out[lo], out[hi] = out[hi], out[lo]

    return out


def ps2_unswizzle_indices(data: bytes, width: int, height: int, bpp: int) -> bytearray:
    """Unswizzle PS2 GS PSMT4/PSMT8 palette indices to one byte per pixel.

    A GS transfer has a minimum footprint per pixel storage mode, so textures
    smaller than that are stored — and swizzled — at the clamped size. Those get
    unswizzled at the padded dimensions and cropped back down afterwards.

    Args:
        data: Swizzled index data (nibble-packed for bpp=4, byte-per-index for bpp=8).
        width: Texture width in pixels (must be a power of two).
        height: Texture height in pixels.
        bpp: 4 or 8 (index bit depth).

    Returns:
        One byte per pixel, each holding the raw palette index.
    """
    min_w, min_h = (32, 4) if bpp == 4 else (16, 4)
    padded_w = max(width, min_w)
    padded_h = max(height, min_h)

    out = bytearray(padded_w * padded_h)

    logw = padded_w.bit_length() - 1
    mask = (1 << (logw + 2)) - 1

    if bpp == 8:
        for y in range(0, padded_h, 4):
            row_off = y << logw
            tmpbuf = data[row_off : row_off + 4 * padded_w]
            for i in range(4):
                for x in range(padded_w):
                    a = ((y + i) << logw) + x
                    s = _ps2_swizzle_addr(x, y + i, logw) & mask
                    if s < len(tmpbuf):
                        out[a] = tmpbuf[s]
    else:
        for y in range(0, padded_h, 4):
            row_off = y << (logw - 1)
            tmpbuf = data[row_off : row_off + 2 * padded_w]
            for i in range(4):
                for x in range(padded_w):
                    a = ((y + i) << logw) + x
                    s = _ps2_swizzle_addr(x, y + i, logw) & mask
                    byte_idx = s >> 1
                    if byte_idx >= len(tmpbuf):
                        continue
                    c = (tmpbuf[byte_idx] >> 4) if (s & 1) else (tmpbuf[byte_idx] & 0xF)
                    out[a] = c

    if (padded_w, padded_h) != (width, height):
        cropped = bytearray(width * height)
        for y in range(height):
            cropped[y * width : (y + 1) * width] = out[
                y * padded_w : y * padded_w + width
            ]
        return cropped

    return out


# ═══════════════════════════════════════════════════════
#  DXT Codec
# ═══════════════════════════════════════════════════════


def _decode_rgb565(c: int) -> tuple[int, int, int]:
    return (
        ((c >> 11) & 0x1F) * 255 // 31,
        ((c >> 5) & 0x3F) * 255 // 63,
        (c & 0x1F) * 255 // 31,
    )


def _encode_rgb565(r: int, g: int, b: int) -> int:
    return ((r * 31 // 255) << 11) | ((g * 63 // 255) << 5) | (b * 31 // 255)


def _decode_dxt_color_block(block: bytes) -> list[tuple[int, int, int, int]]:
    c0: int = struct.unpack_from("<H", block, 0)[0]
    c1: int = struct.unpack_from("<H", block, 2)[0]
    r0, g0, b0 = _decode_rgb565(c0)
    r1, g1, b1 = _decode_rgb565(c1)

    colors: list[tuple[int, int, int, int]] = [(r0, g0, b0, 255), (r1, g1, b1, 255)]
    if c0 > c1:
        colors.append(((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255))
        colors.append(((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255))
    else:
        colors.append(((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255))
        colors.append((0, 0, 0, 0))

    lookup: int = struct.unpack_from("<I", block, 4)[0]
    pixels: list[tuple[int, int, int, int]] = []
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
            block_pixels: list[tuple[int, int, int, int]] = []
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
    tex.struct.has_alpha = has_alpha

    if dxt:
        # DXT compressed
        tex.struct.dxt_compression = dxt
        tex.struct.raster_format = RWTextureRasterFormat(
            RWTextureFormat.FORMAT_8888, False, False, False, True
        )
        tex.struct.bitdeph = 16  # DXT block depth

        mip_rgba = bytes(rgba)
        w, h = width, height
        while True:
            compressed = encode_dxt1(mip_rgba, w, h)
            tex.struct.mipmaps.append(MipmapLevel(w, h, len(compressed), compressed))
            if not generate_mipmaps or (w <= 4 and h <= 4):
                break
            mip_rgba = bytes(_downsample_rgba(mip_rgba, w, h))
            w = max(w // 2, 4)
            h = max(h // 2, 4)

    elif depth == 8:
        # Palettized PAL8
        tex.struct.raster_format = RWTextureRasterFormat(
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
            mip_rgba = bytes(rgba)
            w, h = width, height
            while w > 1 or h > 1:
                mip_rgba = bytes(_downsample_rgba(mip_rgba, w, h))
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
            mip_rgba = bytes(rgba)
            w, h = width, height
            while w > 1 or h > 1:
                mip_rgba = bytes(_downsample_rgba(mip_rgba, w, h))
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
            mip_rgba = bytes(rgba)
            w, h = width, height
            while w > 1 or h > 1:
                mip_rgba = bytes(_downsample_rgba(mip_rgba, w, h))
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

    # An opaque texture only needs RGB. Assign the format field rather than
    # rebuilding the whole raster format: replacing it drops the pal4/pal8
    # flags, and a reader that doesn't know a palette is present would take
    # the palette bytes for texels. Palettized textures keep 8888 either way,
    # which is what the game's own dictionaries do.
    if (
        not has_alpha
        and not tex.struct.raster_format.pal4
        and not tex.struct.raster_format.pal8
        and tex.struct.raster_format.format == RWTextureFormat.FORMAT_8888
    ):
        tex.struct.raster_format.format = RWTextureFormat.FORMAT_888

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


def _quantize_to_palette(
    rgba: bytes, w: int, h: int, max_colors: int
) -> tuple[list[PaletteEntry], bytearray]:
    """Simple median-cut-ish palette quantization. Returns (palette, indices)."""
    # Collect unique colors
    color_counts: dict[tuple[int, int, int, int], int] = {}
    pixels: list[tuple[int, int, int, int]] = []
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
        palette: list[PaletteEntry] = []
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


def pixels_to_idx(
    pixels: list[tuple[int, int, int, int]],
    color_to_idx: dict[tuple[int, int, int, int], int],
) -> bytearray:
    return bytearray(color_to_idx.get(p, 0) for p in pixels)


def _quantize_with_palette(
    rgba: bytes, w: int, h: int, palette: list[PaletteEntry]
) -> bytearray:
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
