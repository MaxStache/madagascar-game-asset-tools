import copy
import uuid
from dataclasses import dataclass
from typing import cast, override

from madagascar.streamfuncs import RW_sf_CreateEntity
from madagascar.streamfuncs.stringfuncs.sf_CreateEntity import (
    RW_sf_CreateEntity_Attribute_TFBReference,
)
from madagascar.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import (
    RW_sf_LoadEmbeddedAsset,
)
from madlysimple.actorparams import CProtoActorParams, SharedActorParams

CLASS_NAME = "CProtoActor"

MODEL_COMMAND = 2
SCRIPT_COMMAND = 3

# What a reference can point at: another entity in the stream (a CTFBModel,
# say) or an embedded asset (a compiled TFBScript).  The two spell their id
# and name differently, hence this.
RefTarget = RW_sf_CreateEntity | RW_sf_LoadEmbeddedAsset


def _targetGuid(target: RefTarget) -> uuid.UUID:
    if isinstance(target, RW_sf_LoadEmbeddedAsset):
        return target.guid
    return target.entityID


def _targetName(target: RefTarget) -> str:
    if isinstance(target, RW_sf_LoadEmbeddedAsset):
        return target.name
    return target.tfbGetName()

@dataclass
class CProtoActor(RW_sf_CreateEntity):
    """A placed actor, with its attributes as read/write properties.
    """

    @classmethod
    def from_entity(cls, entity: RW_sf_CreateEntity) -> "CProtoActor":
        # Re-tag in place instead of copying, so writes through the properties
        # land on the very entity the stream holds.
        if entity.find_first_class(CLASS_NAME) is None:
            raise ValueError(
                f"Entity {entity.tfbGetName()!r} has no {CLASS_NAME} attribute class"
            )
        entity.__class__ = cls
        return cast(CProtoActor, entity)

    @property
    def params(self) -> CProtoActorParams:
        return CProtoActorParams(self, CLASS_NAME, 1)

    @property
    def sharedParams(self) -> SharedActorParams:
        return SharedActorParams(self, CLASS_NAME, 1)

    def _ref(self, command: int) -> RW_sf_CreateEntity_Attribute_TFBReference:
        """The reference at `command`, or an empty one if the actor has none."""
        attr = self.getAttributeSoft(CLASS_NAME, command)
        if attr is None:
            return RW_sf_CreateEntity_Attribute_TFBReference()
        return attr.asTfbRef()

    def _setRef(
        self, command: int, ref: RW_sf_CreateEntity_Attribute_TFBReference
    ) -> None:
        self.getAttributeOrCreate(CLASS_NAME, command).setTfbRef(ref)

    @property
    def modelRef(self) -> RW_sf_CreateEntity_Attribute_TFBReference:
        """The CTFBModel this actor draws as, as ``"{GUID}  name"``.

        A snapshot: editing the returned object changes nothing on the entity.
        Assign a whole reference back, or use `setModelRef` / `modelGuid` /
        `modelName`.
        """
        return self.getAttribute(CLASS_NAME, MODEL_COMMAND).asTfbRef()

    @modelRef.setter
    def modelRef(self, value: RW_sf_CreateEntity_Attribute_TFBReference) -> None:
        self._setRef(MODEL_COMMAND, value)

    def setModelRef(self, target: RefTarget) -> None:
        """Draw this actor as `target`, filling in both its id and its name."""
        self.modelRef = RW_sf_CreateEntity_Attribute_TFBReference(
            index=-1, guid=_targetGuid(target), name=_targetName(target)
        )

    @property
    def modelGuid(self) -> uuid.UUID:
        return self.modelRef.guid

    @modelGuid.setter
    def modelGuid(self, value: uuid.UUID) -> None:
        ref = self._ref(MODEL_COMMAND)
        ref.guid = value
        self.modelRef = ref

    @property
    def modelName(self) -> str | None:
        """Only a label -- the engine matches on the GUID, not on this."""
        return self.modelRef.name

    @modelName.setter
    def modelName(self, value: str | None) -> None:
        ref = self._ref(MODEL_COMMAND)
        ref.name = value
        self.modelRef = ref

    @property
    def scriptRef(self) -> RW_sf_CreateEntity_Attribute_TFBReference | None:
        """The bound TFBScript as ``"{GUID}  "``, or None if the actor has none.

        A snapshot, exactly like `modelRef`.
        """
        attr = self.getAttributeSoft(CLASS_NAME, SCRIPT_COMMAND)
        return None if attr is None else attr.asTfbRef()

    @scriptRef.setter
    def scriptRef(self, value: RW_sf_CreateEntity_Attribute_TFBReference) -> None:
        self._setRef(SCRIPT_COMMAND, value)

    def setScriptRef(self, target: RefTarget) -> None:
        """Run `target` on this actor.

        No name is written: every one of the 5080 script references in the
        shipped levels carries the GUID alone.
        """
        self.scriptRef = RW_sf_CreateEntity_Attribute_TFBReference(
            index=-1, guid=_targetGuid(target), name=None
        )

    @property
    def scriptGuid(self) -> uuid.UUID | None:
        ref = self.scriptRef
        return None if ref is None else ref.guid

    @scriptGuid.setter
    def scriptGuid(self, value: uuid.UUID) -> None:
        ref = self._ref(SCRIPT_COMMAND)
        ref.guid = value
        self.scriptRef = ref

    @property
    def flagBytes(self) -> bytes:
        """Four independent byte flags copied to actor+0x2ec..0x2ef.

        0xffffffff in all shipped data; possibly an unused tint colour.
        """
        return self.getAttribute(CLASS_NAME, 6).data[:4]

    @flagBytes.setter
    def flagBytes(self, value: bytes) -> None:
        if len(value) != 4:
            raise ValueError(f"Expected 4 bytes, got {len(value)}")
        self.getAttributeOrCreate(CLASS_NAME, 6, default_data=b"\xFF\xFF\xFF\xFF").data = bytes(value)




    @override
    def duplicate(self) -> "CProtoActor":
        return copy.deepcopy(self)