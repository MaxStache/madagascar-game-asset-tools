from enum import Enum
import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from formats.lib.writer import _write_u32, _write_u16
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise, library_id_unpack

from formats.sections.TEXTURENATIVE_0015 import RW_TextureNative
from formats.sections.EXTENSION_0003 import RW_Extension

class RW_TextureDictionary_DeviceId(Enum):
    D3D8 = 1
    D3D9 = 2
    PS2 = 6
    XBOX = 8
    PS3 = 10

@dataclass
class RW_TextureDictionary_Struct(RW_Section):
    """https://gtamods.com/wiki/Texture_Dictionary_(RW_Section)"""
    header: RWHeader = field(default_factory=RWHeader)
    
    # if version > 0x3600
    textureCount: int = 0 # u16 - determines count of Raster sections

    deviceId: RW_TextureDictionary_DeviceId = RW_TextureDictionary_DeviceId.D3D8
    # else
    textureCount: int = 0 # u32 - determines count of Raster sections
    # endif

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_TextureDictionary_Struct":
        texdict_s = RW_TextureDictionary_Struct()
        texdict_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texdict_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_TextureDictionary_Struct chunk type",
        )

        if texdict_s.header.version > 0x3600:
            texdict_s.textureCount = parser.readUint16()
            texdict_s.deviceId = RW_TextureDictionary_DeviceId(parser.readUint16())
        else:
            texdict_s.textureCount = parser.readUint32()

        return texdict_s

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        if library_id_unpack(stamp)[0] > 0x3600:
            _write_u16(buf, this.textureCount)
            _write_u16(buf, this.deviceId.value)
        else:
            _write_u32(buf, this.textureCount)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

@dataclass
class RW_TextureDictionary(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    
    struct: RW_TextureDictionary_Struct = field(default_factory=RW_TextureDictionary_Struct)

    textures: list[RW_TextureNative] = field(default_factory=list)

    extension: RW_Extension = field(default_factory=RW_Extension)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_TextureDictionary":
        texdict = RW_TextureDictionary()
        texdict.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texdict.header,
            RWSectionType.rwID_TEXDICTIONARY.value,
            "RW_TextureDictionary chunk type",
        )

        texdict.struct = RW_TextureDictionary_Struct.read(parser, parent=texdict)

        for _ in range(texdict.struct.textureCount):
            tex = RW_TextureNative.read(parser, parent=texdict)
            texdict.textures.append(tex)

        texdict.extension = RW_Extension.read(parser, parent=texdict)

        return texdict

    def write(this, f, stamp, parent=None):
        if isinstance(f, (str, os.PathLike)):
            with open(f, "wb") as out:
                this.write(out, stamp, parent=parent)
            return

        buf = io.BytesIO()

        this.struct.write(buf, stamp, parent=this)

        for tex in this.textures:
            tex.write(buf, stamp, parent=this)

        this.extension.write(buf, stamp, parent=this)

        rw_header = RWHeader(
            type=RWSectionType.rwID_TEXDICTIONARY.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
    
    
    def export_all(this, output_dir: Union[str, Path], raise_on_error: bool = True):
        """Export all textures in a TXD to PNG files.

        Args:
            output_dir: Directory to write PNGs into (created if needed).
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, tex in enumerate(this.textures):
            name = tex.struct.name if tex.struct.name else f"texture_{i}"
            out_path = output_dir / f"{name}.png"
            try:
                tex.export_png(out_path)
            except Exception as e:
                if raise_on_error:
                    raise RuntimeError(f"Failed to export texture {name} to {out_path}: {e}") from e
                else:
                    print(f"  Failed to export {name}: {e}")

    def add_texture(this, texture: RW_TextureNative):
        """Add a texture to the dictionary an update textureCount"""
        this.textures.append(texture)
        this.struct.textureCount = len(this.textures)

    def find_texture_by_name(this, name: str) -> RW_TextureNative:
        """Find a texture by name in the dictionary."""
        for tex in this.textures:
            if tex.struct.name == name:
                return tex
        return None