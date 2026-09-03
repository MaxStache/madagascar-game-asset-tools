import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from madagascar.lib.parser import Parser
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RpTFBUVAnimation:
    uScrollRate: float = field(default=0.0)
    vScrollRate: float = field(default=0.0)

    uAmplitude: float = field(default=0.0)
    vAmplitude: float = field(default=0.0)

    uFrequency: float = field(default=0.0)
    vFrequency: float = field(default=0.0)

    uPhase: float = field(default=0.0)
    vPhase: float = field(default=0.0)

    @classmethod
    def read(cls, parser: Parser) -> "RpTFBUVAnimation":
        anim = cls()

        anim.uScrollRate = parser.readFloat()
        anim.vScrollRate = parser.readFloat()

        anim.uAmplitude = parser.readFloat()
        anim.vAmplitude = parser.readFloat()

        anim.uFrequency = parser.readFloat()
        anim.vFrequency = parser.readFloat()

        anim.uPhase = parser.readFloat()
        anim.vPhase = parser.readFloat()

        return anim
        

@dataclass
class RpTFBMaterialFlags:
    enableAnimation: bool = (
        False  # 0x0001 — enables per-frame animation (UV / flipbook / curve updates)
    )
    uvTransform: bool = (
        False  # 0x0002 — eight UV floats are present; creates MatFX UV transform
    )
    unknown_0008: bool = False  # 0x0008 — unknown
    unknown_0200: bool = False  # 0x0200 — unknown
    stencilWrite: bool = False  # 0x0400 — writes material pixels into stencil buffer

    # Runtime-only flags (not stored on disk)
    runtime_transparent: bool = False  # 0x0020 — material fully transparent
    runtime_colorCached: bool = False  # 0x0040 — original material color cached
    runtime_alphaModulation: bool = False  # 0x0080 — alpha modulation active
    runtime_colorChanged: bool = False  # 0x0100 — material color changed this frame

    @staticmethod
    def decode(value: int) -> "RpTFBMaterialFlags":
        f = RpTFBMaterialFlags()

        # Disk flags
        f.enableAnimation = bool(value & 0x0001)
        f.uvTransform = bool(value & 0x0002)
        f.unknown_0008 = bool(value & 0x0008)
        f.unknown_0200 = bool(value & 0x0200)
        f.stencilWrite = bool(value & 0x0400)

        # Runtime flags
        f.runtime_transparent = bool(value & 0x0020)
        f.runtime_colorCached = bool(value & 0x0040)
        f.runtime_alphaModulation = bool(value & 0x0080)
        f.runtime_colorChanged = bool(value & 0x0100)

        return f


@dataclass
class RW_TFB_TFBMaterial(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    version: int = field(default=0x0F0F000D)

    flags: RpTFBMaterialFlags = field(default_factory=RpTFBMaterialFlags)

    blendMode: int = field(default=3)

    alphaTestRef: int = field(default=2)

    alphaTestFunc: int = field(default=5)

    uvAnim: RpTFBUVAnimation = field(default_factory=RpTFBUVAnimation)

    numTexSets: int = field(default=0)

    hasColourCurve: bool = field(default=False)
    hasAlphaCurve: bool = field(default=False)

    unknown_2D8: int = field(default=0) # Seen: 0,1,2

    @classmethod
    @override
    def read(
        cls, parser: Parser, parent: RW_Section | None = None
    ) -> "RW_TFB_TFBMaterial":
        tfbmat = cls()
        tfbmat.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            tfbmat.header,
            0x800000F6,
            "RW_TFB_TFBMaterial chunk type",
        )

        tfbmat.version = parser.readUint32()
        tfbmat.flags = RpTFBMaterialFlags.decode(parser.readUint32())

        tfbmat.blendMode = parser.readUint32()
        tfbmat.alphaTestRef = parser.readUint32()
        tfbmat.alphaTestFunc = parser.readUint32()

        if tfbmat.flags.uvTransform:
            tfbmat.uvAnim = RpTFBUVAnimation.read(parser)

        tfbmat.numTexSets = parser.readUint32()
        tfbmat.hasColourCurve = parser.readUint32()
        tfbmat.hasAlphaCurve = parser.readUint32()
        tfbmat.unknown_2D8 = parser.readUint8()

        return tfbmat

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=0x800000F6,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
