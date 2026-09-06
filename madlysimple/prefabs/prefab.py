from dataclasses import dataclass
from typing import cast

from madagascar.lib.parser import Parser
from madagascar.lib.rw_basics import RW_StreamFunc
from madagascar.stream import RW_StreamFile
from madagascar.streamfuncs.stringfuncs.sf_CreateEntity import RW_sf_CreateEntity
from madagascar.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import RW_sf_LoadEmbeddedAsset
from ..cprotoactor import CProtoActor


def find_unique_name(level: RW_StreamFile, name: str) -> str:
    i = 0

    while level.entityByNameSoft(f"{name}_Copy{i:02}") is not None:
        i += 1

    return f"{name}_Copy{i:02}"


@dataclass
class Prefab:
    actor: CProtoActor
    context: RW_StreamFile

    @classmethod
    def create(cls, actor: CProtoActor | RW_sf_CreateEntity, context: RW_StreamFile):
        if actor.behaviour != "CProtoActor":
            raise ValueError(
                "Trying to create a prefab with a non CProtoActor is not possible, you passed an entity with the behavior: "
                + actor.behaviour
                + "\nThis can happen when you fetch an entity by its name but there are multiple entites with that name, try finding by name and behavior"
            )

        return cls(actor=CProtoActor.from_entity(actor), context=context)

    def place(self, level: RW_StreamFile) -> RW_sf_CreateEntity:
        new_actor = self.actor.duplicate()

        # === Create a new identity for the copy ===
        new_actor.setRandomEntityId()

        new_name = find_unique_name(level, new_actor.tfbGetName())
        new_actor.tfbSetName(new_name)
        # ==========================================

        # ====== Queue the referenced assets ======

        SF_REQUIREMENT_QUEUE: list[RW_StreamFunc] = []

        if new_actor.modelRef:
            resolved = new_actor.modelRef.resolveSoft(self.context)
            if resolved:
                # An asset has to be loaded before the entity that consumes it,
                # so the model's assets are queued ahead of the model entity.

                # Animations
                for attr in cast(RW_sf_CreateEntity, resolved).getAttributes("CTFBModel", 3):
                    resolved_anim_asset = attr.asTfbRef().resolveSoft(self.context)
                    if resolved_anim_asset is None:
                        continue

                    SF_REQUIREMENT_QUEUE.append(resolved_anim_asset)

                # Attached resources (e.g. the .dff mesh and default .anm)
                for attr in cast(RW_sf_CreateEntity, resolved).getAttributes("CSystemCommands", 0):
                    resource_guid = Parser(attr.data).readGUID()
                    resolved_resource = self.context.assetByIDSoft(resource_guid) or self.context.entityByIDSoft(resource_guid)
                    if resolved_resource is None:
                        continue

                    SF_REQUIREMENT_QUEUE.append(resolved_resource)

                SF_REQUIREMENT_QUEUE.append(
                    resolved
                )

        if new_actor.scriptRef:
            resolved = new_actor.scriptRef.resolveSoft(self.context)
            if resolved:
                SF_REQUIREMENT_QUEUE.append(
                    resolved
                )

        # ==========================================

        for req in SF_REQUIREMENT_QUEUE:
            if isinstance(req, RW_sf_CreateEntity):
                if any(req.entityID == e.entityID for e in level.entities()):
                    continue # This entity is already in the level

                level.append(req.duplicate())


            elif isinstance(req, RW_sf_LoadEmbeddedAsset):
                if any(req.guid == e.guid for e in level.embeddedAssets()):
                    continue # This asset is already in the level

                level.append(req.duplicate())



            else:
                print(req.__class__.__name__)
                raise TypeError("We queued a stream func which isnt handled, this should NOT happen, huh")

        # ==========================================

        level.append(new_actor)

        return new_actor
