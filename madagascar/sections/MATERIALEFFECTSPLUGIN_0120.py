from enum import Enum
import io
from dataclasses import dataclass, field
from typing import BinaryIO, ClassVar, override

from madagascar.lib.writer import write_u32, write_s32, write_f32
from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from madagascar.sections.TEXTURE_0006 import RW_Texture


class RW_MaterialEffectsPlugin_EffectType(Enum):
    rwMATFXEFFECTNULL = 0x00  # No Effect
    rwMATFXEFFECTBUMPMAP = 0x01  # Bump Map
    rwMATFXEFFECTENVMAP = 0x02  # Environment Map (Reflections)
    rwMATFXEFFECTBUMPENVMAP = 0x03  # Bump Map/Environment Map
    rwMATFXEFFECTDUAL = 0x04  # Dual Textures
    rwMATFXEFFECTUVTRANSFORM = 0x05  # UV-Tranformation
    rwMATFXEFFECTDUALUVTRANSFORM = 0x06  # Dual Textures/UV-Transformation


class RW_MaterialEffectsPlugin_Variant(Enum):
    MaterialExtension = 0  # On Material
    AtomicExtension = 1  # On Atomic


def _parent_is_atomic(parent: RW_Section | None) -> bool:
    """
    Whether the extension's parent chunk is an Atomic (or Atomic Sector).

    ``parent.header.type`` may be a raw ``int`` (a ``RWSectionType.*.value``) or an
    ``RWSectionType`` member, depending on the caller, so normalise to ``int``.
    """
    if parent is None:
        return False
    assert hasattr(parent, "header")
    return parent.header.type in ( # type: ignore
        RWSectionType.rwID_ATOMICSECT.value,
        RWSectionType.rwID_ATOMIC.value,
    )


# ---------------------------------------------------------------------------
# Effect "slots"
#
# A material extension always stores two effect slots back to back. Each slot
# is self-describing: it starts with its own ``effectType`` uint32, followed by
# effect-specific data. One dataclass models one effect type; the base class
# handles the shared read-dispatch / write-header plumbing.
#
# ~ https://gtamods.com/wiki/Material_Effects_PLG_(RW_Section)
# ---------------------------------------------------------------------------


@dataclass
class RW_MaterialEffectsPlugin_Effect:
    """Base class for a single effect slot. Subclass per effect type."""

    # Overridden by every concrete subclass. Not a dataclass field.
    EFFECT_TYPE: ClassVar[RW_MaterialEffectsPlugin_EffectType] = (
        RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTNULL
    )

    @staticmethod
    def read(parser: Parser) -> "RW_MaterialEffectsPlugin_Effect":
        effect_type = RW_MaterialEffectsPlugin_EffectType(parser.readUint32())
        cls = _EFFECT_REGISTRY.get(effect_type, RW_MatFXEffectNull)
        return cls._read_body(parser)

    @classmethod
    def _read_body(cls, parser: Parser) -> "RW_MaterialEffectsPlugin_Effect":
        # Effects without a body (Null / UV Transform) rely on this default.
        return cls()

    def write(self, f: BinaryIO, stamp: int):
        write_u32(f, self.EFFECT_TYPE.value)
        self._write_body(f, stamp)

    def _write_body(self, f: BinaryIO, stamp: int):
        # No body by default.
        pass


@dataclass
class RW_MatFXEffectNull(RW_MaterialEffectsPlugin_Effect):
    """No effect. Header only."""

    EFFECT_TYPE: ClassVar = RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTNULL


@dataclass
class RW_MatFXEffectBumpMap(RW_MaterialEffectsPlugin_Effect):
    """Bump mapping. Optionally carries a bump texture and/or height texture."""

    EFFECT_TYPE: ClassVar = RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTBUMPMAP

    intensity: float = 0.0  # float32
    hasBumpMap: bool = False  # uint32 (bool32)
    bumpMap: RW_Texture | None = None  # RW_Texture, present if hasBumpMap
    hasHeightMap: bool = False  # uint32 (bool32)
    heightMap: RW_Texture | None = None  # RW_Texture, present if hasHeightMap

    @classmethod
    @override
    def _read_body(cls, parser: Parser) -> "RW_MatFXEffectBumpMap":
        e = cls()
        e.intensity = parser.readFloat()
        e.hasBumpMap = bool(parser.readUint32())
        if e.hasBumpMap:
            e.bumpMap = RW_Texture.read(parser)
        e.hasHeightMap = bool(parser.readUint32())
        if e.hasHeightMap:
            e.heightMap = RW_Texture.read(parser)
        return e

    @override
    def _write_body(self, f, stamp):
        write_f32(f, self.intensity)
        write_u32(f, int(bool(self.hasBumpMap)))
        if self.hasBumpMap:
            assert self.bumpMap is not None
            self.bumpMap.write(f, stamp)
        write_u32(f, int(bool(self.hasHeightMap)))
        if self.hasHeightMap:
            assert self.heightMap is not None
            self.heightMap.write(f, stamp)


@dataclass
class RW_MatFXEffectEnvMap(RW_MaterialEffectsPlugin_Effect):
    """Environment mapping (reflections). Optionally carries an env texture."""

    EFFECT_TYPE: ClassVar = RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTENVMAP

    reflectionCoefficient: float = 0.0  # float32
    useFrameBufferAlpha: bool = False  # uint32 (bool32)
    hasEnvMap: bool = False  # uint32 (bool32)
    envMap: RW_Texture | None = None  # RW_Texture, present if hasEnvMap

    @classmethod
    @override
    def _read_body(cls, parser: Parser) -> "RW_MatFXEffectEnvMap":
        e = cls()
        e.reflectionCoefficient = parser.readFloat()
        e.useFrameBufferAlpha = bool(parser.readUint32())
        e.hasEnvMap = bool(parser.readUint32())
        if e.hasEnvMap:
            e.envMap = RW_Texture.read(parser)
        return e

    @override
    def _write_body(self, f, stamp):
        write_f32(f, self.reflectionCoefficient)
        write_u32(f, int(bool(self.useFrameBufferAlpha)))
        write_u32(f, int(bool(self.hasEnvMap)))
        if self.hasEnvMap:
            assert self.envMap is not None
            self.envMap.write(f, stamp)


@dataclass
class RW_MatFXEffectDual(RW_MaterialEffectsPlugin_Effect):
    """Dual texturing. Optionally carries a second texture."""

    EFFECT_TYPE: ClassVar = RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTDUAL

    srcBlendMode: int = 0  # int32
    dstBlendMode: int = 0  # int32
    hasTexture: bool = False  # uint32 (bool32)
    texture: RW_Texture | None = None  # RW_Texture, present if hasTexture

    @classmethod
    @override
    def _read_body(cls, parser: Parser) -> "RW_MatFXEffectDual":
        e = cls()
        e.srcBlendMode = parser.readInt32()
        e.dstBlendMode = parser.readInt32()
        e.hasTexture = bool(parser.readUint32())
        if e.hasTexture:
            e.texture = RW_Texture.read(parser)
        return e

    @override
    def _write_body(self, f, stamp):
        write_s32(f, self.srcBlendMode)
        write_s32(f, self.dstBlendMode)
        write_u32(f, int(bool(self.hasTexture)))
        if self.hasTexture:
            assert self.texture is not None
            self.texture.write(f, stamp)


@dataclass
class RW_MatFXEffectUVTransform(RW_MaterialEffectsPlugin_Effect):
    """UV animation. Header only in this chunk."""

    EFFECT_TYPE: ClassVar = RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTUVTRANSFORM


_EFFECT_REGISTRY: dict[
    RW_MaterialEffectsPlugin_EffectType, type[RW_MaterialEffectsPlugin_Effect]
] = {
    RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTNULL: RW_MatFXEffectNull,
    RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTBUMPMAP: RW_MatFXEffectBumpMap,
    RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTENVMAP: RW_MatFXEffectEnvMap,
    RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTDUAL: RW_MatFXEffectDual,
    RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTUVTRANSFORM: RW_MatFXEffectUVTransform,
}


@dataclass
class RW_MaterialEffectsPlugin(RW_Section):
    """
    Material Effects PLG (rwID_MATERIALEFFECTSPLUGIN, 0x0120).

    This chunk appears as an extension on two different parents and its layout
    depends on which one:

    * Material extension (``MaterialExtension``): a top-level ``effectType``
      uint32 followed by two effect "slots" (see RW_MaterialEffectsPlugin_Effect).
      Combined effects (BUMPENVMAP / DUALUVTRANSFORM) are expressed by populating
      both slots with the respective single effects.
    * Atomic extension (``AtomicExtension``): a single ``matFXEnabled`` bool32
      telling whether the material's MatFX pipeline is applied on this atomic.
      In RW versions >= 3.4.0.0 this chunk is only written when the value is 1.

    ~ https://gtamods.com/wiki/Material_Effects_PLG_(RW_Section)
    """

    header: RWHeader = field(default_factory=RWHeader)

    variant: RW_MaterialEffectsPlugin_Variant = field(
        default=RW_MaterialEffectsPlugin_Variant.MaterialExtension
    )

    # --- Atomic extension (variant == AtomicExtension) ---
    matFXEnabled: int = field(default=0)  # uint32 (bool32) - 0 or 1

    # --- Material extension (variant == MaterialExtension) ---
    effectType: RW_MaterialEffectsPlugin_EffectType = field(
        default=RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTNULL
    )  # uint32 - overall effect type header
    effects: list[RW_MaterialEffectsPlugin_Effect] = field(
        default_factory=list
    )  # always two slots

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_MaterialEffectsPlugin":
        matfx = cls()
        matfx.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            matfx.header,
            RWSectionType.rwID_MATERIALEFFECTSPLUGIN.value,
            "RW_MaterialEffectsPlugin chunk type",
        )

        if _parent_is_atomic(parent):
            matfx.variant = RW_MaterialEffectsPlugin_Variant.AtomicExtension
            matfx.matFXEnabled = parser.readUint32()
        else:
            matfx.variant = RW_MaterialEffectsPlugin_Variant.MaterialExtension
            matfx.effectType = RW_MaterialEffectsPlugin_EffectType(parser.readUint32())
            matfx.effects = [
                RW_MaterialEffectsPlugin_Effect.read(parser) for _ in range(2)
            ]

        return matfx

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        if self.variant == RW_MaterialEffectsPlugin_Variant.AtomicExtension:
            write_u32(buf, int(self.matFXEnabled))
        else:
            write_u32(buf, self.effectType.value)
            for effect in self.effects:
                assert isinstance(effect, RW_MaterialEffectsPlugin_Effect)
                effect.write(buf, stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATERIALEFFECTSPLUGIN.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    @override
    def __repr__(self):
        if self.variant == RW_MaterialEffectsPlugin_Variant.AtomicExtension:
            return f"RW_MaterialEffectsPlugin(header={self.header!r},variant={self.variant!r}, matFXEnabled={self.matFXEnabled!r})"
        else:
            return f"RW_MaterialEffectsPlugin(header={self.header!r},variant={self.variant!r}, effectType={self.effectType!r},effects={self.effects!r})"
