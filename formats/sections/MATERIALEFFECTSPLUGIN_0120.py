from enum import Enum
import io
from dataclasses import dataclass, field
from typing import ClassVar, Optional

from ..lib.writer import _write_u32, _write_s32, _write_f32
from ..lib.parser import Parser
from ..rwConstants import RWSectionType
from ..rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from .TEXTURE_0006 import RW_Texture


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


def _parent_is_atomic(parent_type) -> bool:
    """
    Whether the extension's parent chunk is an Atomic (or Atomic Sector).

    ``parent_type`` may be a raw ``int`` (a ``RWSectionType.*.value``) or an
    ``RWSectionType`` member, depending on the caller, so normalise to ``int``.
    """
    if parent_type is None:
        return False
    if isinstance(parent_type, RWSectionType):
        parent_type = parent_type.value
    return parent_type in (
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

    def write(self, f, stamp):
        _write_u32(f, self.EFFECT_TYPE.value)
        self._write_body(f, stamp)

    def _write_body(self, f, stamp):
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
    bumpMap: Optional[RW_Texture] = None  # RW_Texture, present if hasBumpMap
    hasHeightMap: bool = False  # uint32 (bool32)
    heightMap: Optional[RW_Texture] = None  # RW_Texture, present if hasHeightMap

    @classmethod
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

    def _write_body(self, f, stamp):
        _write_f32(f, self.intensity)
        _write_u32(f, int(bool(self.hasBumpMap)))
        if self.hasBumpMap:
            self.bumpMap.write(f, stamp)
        _write_u32(f, int(bool(self.hasHeightMap)))
        if self.hasHeightMap:
            self.heightMap.write(f, stamp)


@dataclass
class RW_MatFXEffectEnvMap(RW_MaterialEffectsPlugin_Effect):
    """Environment mapping (reflections). Optionally carries an env texture."""

    EFFECT_TYPE: ClassVar = RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTENVMAP

    reflectionCoefficient: float = 0.0  # float32
    useFrameBufferAlpha: bool = False  # uint32 (bool32)
    hasEnvMap: bool = False  # uint32 (bool32)
    envMap: Optional[RW_Texture] = None  # RW_Texture, present if hasEnvMap

    @classmethod
    def _read_body(cls, parser: Parser) -> "RW_MatFXEffectEnvMap":
        e = cls()
        e.reflectionCoefficient = parser.readFloat()
        e.useFrameBufferAlpha = bool(parser.readUint32())
        e.hasEnvMap = bool(parser.readUint32())
        if e.hasEnvMap:
            e.envMap = RW_Texture.read(parser)
        return e

    def _write_body(self, f, stamp):
        _write_f32(f, self.reflectionCoefficient)
        _write_u32(f, int(bool(self.useFrameBufferAlpha)))
        _write_u32(f, int(bool(self.hasEnvMap)))
        if self.hasEnvMap:
            self.envMap.write(f, stamp)


@dataclass
class RW_MatFXEffectDual(RW_MaterialEffectsPlugin_Effect):
    """Dual texturing. Optionally carries a second texture."""

    EFFECT_TYPE: ClassVar = RW_MaterialEffectsPlugin_EffectType.rwMATFXEFFECTDUAL

    srcBlendMode: int = 0  # int32
    dstBlendMode: int = 0  # int32
    hasTexture: bool = False  # uint32 (bool32)
    texture: Optional[RW_Texture] = None  # RW_Texture, present if hasTexture

    @classmethod
    def _read_body(cls, parser: Parser) -> "RW_MatFXEffectDual":
        e = cls()
        e.srcBlendMode = parser.readInt32()
        e.dstBlendMode = parser.readInt32()
        e.hasTexture = bool(parser.readUint32())
        if e.hasTexture:
            e.texture = RW_Texture.read(parser)
        return e

    def _write_body(self, f, stamp):
        _write_s32(f, self.srcBlendMode)
        _write_s32(f, self.dstBlendMode)
        _write_u32(f, int(bool(self.hasTexture)))
        if self.hasTexture:
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

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_MaterialEffectsPlugin":
        matfx = RW_MaterialEffectsPlugin()
        matfx.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            matfx.header,
            RWSectionType.rwID_MATERIALEFFECTSPLUGIN.value,
            "RW_MaterialEffectsPlugin chunk type",
        )

        if _parent_is_atomic(parent_type):
            matfx.variant = RW_MaterialEffectsPlugin_Variant.AtomicExtension
            matfx.matFXEnabled = parser.readUint32()
        else:
            matfx.variant = RW_MaterialEffectsPlugin_Variant.MaterialExtension
            matfx.effectType = RW_MaterialEffectsPlugin_EffectType(parser.readUint32())
            matfx.effects = [
                RW_MaterialEffectsPlugin_Effect.read(parser) for _ in range(2)
            ]

        return matfx

    def write(this, f, stamp):
        buf = io.BytesIO()

        if this.variant == RW_MaterialEffectsPlugin_Variant.AtomicExtension:
            _write_u32(buf, int(this.matFXEnabled))
        else:
            _write_u32(buf, this.effectType.value)
            for effect in this.effects:
                effect.write(buf, stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATERIALEFFECTSPLUGIN.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
