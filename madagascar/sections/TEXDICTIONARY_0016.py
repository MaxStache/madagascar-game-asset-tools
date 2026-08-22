from enum import Enum
import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, override

from madagascar.lib.writer import write_u32, write_u16
from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise, library_id_unpack

from madagascar.sections.TEXTURENATIVE_0015 import RW_TextureNative
from madagascar.sections.EXTENSION_0003 import RW_Extension

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
    # textureCount: int = 0 # u32 - determines count of Raster sections
    # endif

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_TextureDictionary_Struct":
        texdict_s = cls()
        texdict_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            texdict_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_TextureDictionary_Struct chunk type",
        )

        if texdict_s.header.version > 0x3600:
            texdict_s.textureCount = parser.readUint16()
            texdict_s.deviceId = RW_TextureDictionary_DeviceId(parser.readUint16())
            print(f"Read RW_TextureDictionary_Struct: textureCount={texdict_s.textureCount}, deviceId={texdict_s.deviceId}")
        else:
            texdict_s.textureCount = parser.readUint32()

        return texdict_s
    
    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        if library_id_unpack(stamp)[0] > 0x3600:
            write_u16(buf, self.textureCount)
            write_u16(buf, self.deviceId.value)
        else:
            write_u32(buf, self.textureCount)

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

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_TextureDictionary":
        texdict = cls()
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

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        if isinstance(f, (str, os.PathLike)):
            with open(f, "wb") as out:
                self.write(out, stamp, parent=parent)
            return

        buf = io.BytesIO()

        self.struct.write(buf, stamp, parent=self)

        for tex in self.textures:
            tex.write(buf, stamp, parent=self)

        self.extension.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_TEXDICTIONARY.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
    
    
    def export_all(
        self,
        output_dir: str | Path,
        raise_on_error: bool = True,
        all_mipmaps: bool = False,
    ):
        """Export all textures in a TXD to PNG files.

        Args:
            output_dir: Directory to write PNGs into (created if needed).
            raise_on_error: Abort on the first failed texture instead of
                reporting it and carrying on.
            all_mipmaps: Write every mipmap level side by side, largest first,
                instead of just the full resolution level.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, tex in enumerate(self.textures):
            name = tex.struct.name if tex.struct.name else f"texture_{i}"
            out_path = output_dir / f"{name}.png"
            try:
                tex.export_png(out_path, all_mipmaps=all_mipmaps)
            except Exception as e:
                if raise_on_error:
                    raise RuntimeError(f"Failed to export texture {name} to {out_path}: {e}") from e
                else:
                    print(f"  Failed to export {name}: {e}")

    def add_texture(self, texture: RW_TextureNative):
        """Add a texture to the dictionary an update textureCount"""
        self.textures.append(texture)
        self.struct.textureCount = len(self.textures)

    def find_texture_by_name(self, name: str) -> RW_TextureNative | None:
        """Find a texture by name in the dictionary."""
        for tex in self.textures:
            if tex.struct.name == name:
                return tex
        return None