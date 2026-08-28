"""The actor parameter record, as write-through attribute views.

`CProtoActor` attribute 1 is one 272-byte blob that the engine copies
straight into the live actor object.  It is really two records glued
together:

    +0x00..0x3f   CProtoActor-only prefix   -> CProtoActorParams
    +0x40..0x10f  shared 208-byte record    -> SharedActorParams

The second half is byte-for-byte the same record `CTFBModel` attribute 1
carries on its own (there at +0x00), which is why it is its own class --
point `SharedActorParams` at a model with ``base=0`` and the same field
names work.

Both classes read and write through to the entity, exactly like the
CameraData properties do: nothing is cached, so an edit lands on the very
entity the stream holds.

    actor.params.activationRange = 300.0
    actor.params.noShadow = True
    actor.sharedParams.update(health=100, weight=20.0)

Field names and offsets come from the engine's own ``::actor`` script
descriptor table -- see the `madagascar-actor-param-block` memory note.
"""

import struct
from typing import Any, ClassVar, overload, override

from madagascar.streamfuncs import RW_sf_CreateEntity


class _Field:
    """One scalar at a fixed offset inside a parameter block.

    A descriptor rather than a property so the whole layout reads as a
    table -- offset, name and doc on one line each.
    """

    _fmt: ClassVar[str] = "<I"

    def __init__(self, offset: int, doc: str = "", readOnly: bool = False) -> None:
        self.offset = offset
        self.readOnly = readOnly
        self.name = ""
        self.__doc__ = doc

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def _coerce(self, value: Any) -> Any:
        return int(value)

    @overload
    def __get__(self, instance: None, owner: type | None = None) -> "_Field": ...

    @overload
    def __get__(
        self, instance: "ActorParamBlock", owner: type | None = None
    ) -> Any: ...

    def __get__(self, instance: "ActorParamBlock | None", owner: type | None = None):
        if instance is None:
            return self
        return instance.readValue(self.offset, self._fmt)

    def __set__(self, instance: "ActorParamBlock", value: Any) -> None:
        if self.readOnly:
            raise AttributeError(
                f"{type(instance).__name__}.{self.name} is read-only "
                "(the engine never reads it back, changing it only risks "
                "breaking the record)"
            )
        instance.writeValue(self.offset, self._fmt, self._coerce(value))


class _FloatField(_Field):
    _fmt: ClassVar[str] = "<f"

    @override
    def _coerce(self, value: Any) -> float:
        return float(value)


class _UIntField(_Field):
    _fmt: ClassVar[str] = "<I"


class _IntField(_Field):
    _fmt: ClassVar[str] = "<i"


class _FlagField(_Field):
    """One bit of the flags bitmask, exposed as a bool."""

    _fmt: ClassVar[str] = "<I"

    def __init__(self, offset: int, bit: int, doc: str = "") -> None:
        super().__init__(offset, doc)
        self.bit = bit

    @overload
    def __get__(self, instance: None, owner: type | None = None) -> "_FlagField": ...

    @overload
    def __get__(
        self, instance: "ActorParamBlock", owner: type | None = None
    ) -> bool: ...

    @override
    def __get__(self, instance: "ActorParamBlock | None", owner: type | None = None):
        if instance is None:
            return self
        return bool((instance.readValue(self.offset, self._fmt) >> self.bit) & 1)

    @override
    def __set__(self, instance: "ActorParamBlock", value: Any) -> None:
        flags: int = instance.readValue(self.offset, self._fmt)
        if value:
            flags |= 1 << self.bit
        else:
            flags &= ~(1 << self.bit) & 0xFFFFFFFF
        instance.writeValue(self.offset, self._fmt, flags)


class ActorParamBlock:
    """Shared machinery: a fixed slice of one entity attribute.

    Subclasses declare their fields as `_Field` descriptors with offsets
    relative to `base`, so the same field table can be pointed at the same
    record wherever it is embedded.
    """

    __slots__ = ("_base", "_command", "_className", "_owner")

    SIZE: ClassVar[int] = 0

    def __init__(
        self,
        owner: RW_sf_CreateEntity,
        className: str = "CProtoActor",
        command: int = 1,
        base: int = 0,
    ) -> None:
        self._owner = owner
        self._className = className
        self._command = command
        self._base = base

    @property
    def base(self) -> int:
        """Byte offset of this record inside the attribute payload."""
        return self._base

    def asBytes(self) -> bytes:
        """Detached copy of just this record's bytes."""
        blob = self._owner.getAttribute(self._className, self._command).data
        return blob[self._base : self._base + self.SIZE]

    def readValue(self, offset: int, fmt: str) -> Any:
        """One struct-format value at `offset` inside this record."""
        blob = self._owner.getAttribute(self._className, self._command).data
        at = self._base + offset
        if at + struct.calcsize(fmt) > len(blob):
            raise ValueError(
                f"{self._className} attribute {self._command} is only "
                f"{len(blob)} bytes, too short to hold offset 0x{at:x}"
            )
        return struct.unpack_from(fmt, blob, at)[0]

    def writeValue(self, offset: int, fmt: str, value: Any) -> None:
        """Overwrite one struct-format value at `offset`, leaving the rest alone."""
        attr = self._owner.getAttribute(self._className, self._command)
        at = self._base + offset
        if at + struct.calcsize(fmt) > len(attr.data):
            raise ValueError(
                f"{self._className} attribute {self._command} is only "
                f"{len(attr.data)} bytes, too short to hold offset 0x{at:x}"
            )
        data = bytearray(attr.data)
        struct.pack_into(fmt, data, at, value)
        attr.data = bytes(data)

    @classmethod
    def fields(cls) -> dict[str, _Field]:
        """Every declared field, in layout order."""
        found: dict[str, _Field] = {}
        for klass in reversed(cls.__mro__):
            for name, value in vars(klass).items():
                if isinstance(value, _Field):
                    found[name] = value
        return found

    def asDict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.fields()}

    def update(self, **values: Any) -> None:
        """Set several fields at once, rejecting names that don't exist."""
        known = self.fields()
        for name, value in values.items():
            if name not in known:
                raise AttributeError(f"{type(self).__name__} has no field {name!r}")
            setattr(self, name, value)

    @override
    def __repr__(self) -> str:
        body = ",\n".join(f"    {n}={v!r}" for n, v in self.asDict().items())
        return f"{type(self).__name__}(\n{body}\n)"


class CProtoActorParams(ActorParamBlock):
    """The CProtoActor-only prefix -- blob +0x00..0x3f, actor +0x1ac.

    Everything here is about *being an actor placed in a level*: when the
    actor wakes up, and how the editor/radar draws it.  The stats live next
    door in `SharedActorParams`.
    """

    SIZE: ClassVar[int] = 0x40

    def __init__(
        self,
        owner: RW_sf_CreateEntity,
        className: str = "CProtoActor",
        command: int = 1,
        base: int = 0x00,
    ) -> None:
        super().__init__(owner, className, command, base)

    version = _UIntField(0x00, "Record format version -- 2 everywhere.", readOnly=True)
    flags = _UIntField(0x04, "Raw flags bitmask; see the bool fields below.")
    activationRange = _FloatField(
        0x08, "Distance at which the actor wakes up and starts ticking. 0 = always on."
    )
    deactivationRange = _FloatField(
        0x0C, "Distance at which it sleeps again. 9999/10000 = never deactivate."
    )
    coneColor = _UIntField(0x10, "Palette index (0/3/4/8) for the debug vision cone.")
    unknown0x14 = _UIntField(0x14, "1 on 5727/5730 actors. No reader found.")
    blipColor = _UIntField(0x18, "Palette index (0/2) for the radar dot.")
    activationRangeFadePercent = _UIntField(
        0x1C, "Fade-in fraction of the activation range. 0 in all shipped data."
    )

    solidCollision = _FlagField(0x04, 0, "Actor blocks other actors.")
    wallClimber = _FlagField(0x04, 1, "Actor can climb walls.")
    wallCollision = _FlagField(0x04, 2, "Actor collides with walls.")
    noShadow = _FlagField(0x04, 3, "Shadow renderer skips this actor.")
    visibleOnRadar = _FlagField(0x04, 4, "Drawn on the radar using blipColor.")
    cutSceneIgnore = _FlagField(
        0x04, 5, "Excluded from normal cut-scene processing outside game mode 3."
    )
    ignoresGroundColor = _FlagField(
        0x04, 6, "Skips ground-tint lighting. Never set in shipped data."
    )
    tiltsWithGround = _FlagField(0x04, 7, "Pitches/rolls to match the ground normal.")
    meshCollider = _FlagField(
        0x04, 8, "Collide against the mesh instead of the box (needs actor+0x2c8)."
    )
    trianglesCollide = _FlagField(
        0x04, 9, "Per-triangle collision (needs actor+0x2c8)."
    )
    unknownBit10 = _FlagField(0x04, 10, "Set on 16 actors; no accessor, no reader.")
    rwClumpFlag0x1000 = _FlagField(
        0x04, 11, "Model-instance ctor applies RW clump flag 0x1000 when set."
    )


class SharedActorParams(ActorParamBlock):
    """The 208-byte record shared with CTFBModel -- the actor's stats.

    On a `CProtoActor` this sits at blob +0x40 (the default); on a
    `CTFBModel` it is the whole of attribute 1, so build it as
    ``SharedActorParams(model, "CTFBModel", 1, 0)``.
    """

    SIZE: ClassVar[int] = 0xD0

    def __init__(
        self,
        owner: RW_sf_CreateEntity,
        className: str = "CProtoActor",
        command: int = 1,
        base: int = 0x40,
    ) -> None:
        super().__init__(owner, className, command, base)

    version = _UIntField(0x00, "Record format version -- 2 everywhere.", readOnly=True)

    # --- jumping / gravity -------------------------------------------------
    jumpCoastFrames = _UIntField(
        0x04, "Frames the jump floats after takeoff before gravity takes over."
    )
    jumpDelay = _UIntField(0x08, "Windup frames between the jump input and takeoff.")
    initialJumpVelocity = _FloatField(0x2C, "Launch speed applied at takeoff.")
    upTopSpeed = _FloatField(0x30, "Terminal upward speed.")
    upAcceleration = _FloatField(0x34, "Upward acceleration while rising.")
    downAcceleration = _FloatField(0x38, "Gravity -- downward acceleration.")
    downTopSpeed = _FloatField(0x3C, "Terminal falling speed.")
    bounceRestitution = _FloatField(0x40, "Elasticity on landing. 0 on nearly all.")

    # --- core stats --------------------------------------------------------
    health = _UIntField(0x0C, "Hit points. 30 on most actors. Script get/set.")
    moveType = _UIntField(0x10, "Locomotion mode enum (0/1/2/4).")
    weight = _FloatField(0x44, "Mass for physics / knockback / push resolution.")
    id = _IntField(0x98, "Designer-assigned numeric id; -1 = unset. Script get/set.")

    # --- ground movement ---------------------------------------------------
    groundTopSpeed = _FloatField(
        0x14, "Max ground speed, and the upper edge of the fast-move anim band."
    )
    groundTurnRate = _FloatField(
        0x18, "Max ground turn rate, deg/s; also drives the lean anims."
    )
    groundAcceleration = _FloatField(0x48, "How fast it reaches groundTopSpeed.")
    groundDeceleration = _FloatField(0x4C, "How fast it stops on the ground.")

    # --- air movement ------------------------------------------------------
    airTopSpeed = _FloatField(0x50, "Horizontal speed cap while airborne.")
    airAcceleration = _FloatField(0x54, "Horizontal air control, accelerating.")
    airDeceleration = _FloatField(0x58, "Horizontal air control, slowing.")
    airTurnRate = _FloatField(0x74, "Turn rate while airborne, deg/s.")

    # --- vision cone -------------------------------------------------------
    coneAngle = _FloatField(0x1C, "Half-angle of the vision / attention cone.")
    coneLength = _FloatField(0x20, "Range of that cone.")
    coneSweepOffset = _FloatField(0x24, "Angular offset while the cone sweeps.")
    unknown0x28 = _FloatField(0x28, "10 or 0, sits with the cone fields. No reader.")

    # --- collision box (feet; the engine scales by 0.5 * 12) ---------------
    hExtent = _FloatField(0x5C, "Collision-box height, in feet.")
    wExtent = _FloatField(0x60, "Collision-box width, in feet.")
    lExtent = _FloatField(0x64, "Collision-box length, in feet.")
    xOffset = _FloatField(0x68, "Box centre offset.")
    yOffset = _FloatField(0x6C, "Box centre offset.")
    zOffset = _FloatField(
        0x70, "Vertical box offset -- usually hExtent/2, so the base sits on the origin."
    )

    # --- locomotion animation rate bands -----------------------------------
    # FUN_004235b0 picks a band from ground speed, then lerps min->max
    # across it and divides by 100 to get the clip playback rate.
    slowestToSlowSpeed = _FloatField(
        0x78, "Speed at which slowest-move gives way to slow-move."
    )
    slowToFastSpeed = _FloatField(
        0x7C, "Speed at which slow-move gives way to fast-move."
    )
    slowestMoveRateMin = _IntField(0x80, "Slowest-move playback rate x100, band bottom.")
    slowestMoveRateMax = _IntField(0x84, "Slowest-move playback rate x100, band top.")
    slowMoveRateMin = _IntField(0x88, "Slow-move playback rate x100, band bottom.")
    slowMoveRateMax = _IntField(0x8C, "Slow-move playback rate x100, band top.")
    fastMoveRateMin = _IntField(0x90, "Fast-move playback rate x100, band bottom.")
    fastMoveRateMax = _IntField(0x94, "Fast-move playback rate x100, band top.")

    # --- dead editor defaults ---------------------------------------------
    unused50 = _FloatField(0xB0, "50 on every actor and model. No reader.", readOnly=True)
    unused100 = _FloatField(0xB4, "100 on every actor and model. No reader.", readOnly=True)
    unused150 = _FloatField(0xB8, "150 on every actor and model. No reader.", readOnly=True)

    def checkAlignment(self) -> bool:
        """True if the dead 50/100/150 triple is where it should be.

        Nothing reads those three floats, which is exactly what makes them a
        cheap sanity check that `base` points at a real shared record.
        """
        return (self.unused50, self.unused100, self.unused150) == (50.0, 100.0, 150.0)
