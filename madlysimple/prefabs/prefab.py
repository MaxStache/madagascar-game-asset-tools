from dataclasses import dataclass
from typing import cast

from madagascar.lib.parser import Parser
from madagascar.lib.rw_basics import RW_StreamFunc
from madagascar.stream import RW_StreamFile
from madagascar.streamfuncs.stringfuncs.sf_CreateEntity import RW_sf_CreateEntity
from madagascar.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import (
    RW_sf_LoadEmbeddedAsset,
)
from ..levelhub import LevelHub
from ..cprotoactor import CProtoActor
from tfbscript import ScriptFile, BinaryReader as TFBScriptBinaryReader
from colorama import init, Fore

init(autoreset=True)

# TODO: We sometimes add assets altough they already are in the level because we match by id, not name and content, this is kinda bad ngl

KNOWN_TFBSCRIPT_BUILTIN_GLOBALS = [
    "players::set::actor",
    " ALL ::sound",
    "controller 1::controller",
    "no controller::controller",
    "Script Time::value",
    "Next Level Auto Load::value",

    "hit actor::message",
    "hit wall::message",
    "hit ground::message",

    "Current Level::value",
    "Cut-scene Active::value",
    "Design Build::value",

    "inactive::set::actor",
    "active::set::sprite",

    "Hardware Metrics::value",

    "message senders::set::actor",
]

_PLACEMENT_COUNT = 0 # keeps track of how many things were addded in the current place()


def find_unique_name(level: RW_StreamFile, name: str) -> str:
    i = 0

    while level.entityByNameSoft(f"{name}_Copy{i:02}") is not None:
        i += 1

    return f"{name}_Copy{i:02}"


def add_actor_from_level_to_level(
    actor: CProtoActor, context: RW_StreamFile, level: RW_StreamFile
) -> CProtoActor | None:
    """Walks actor and adds it to level, also adds all needed / referenced assets"""

    global _PLACEMENT_COUNT

    # ====== Queue the referenced assets ======

    SF_REQUIREMENT_QUEUE: list[RW_StreamFunc] = []

    if actor.modelRef:
        resolved = actor.modelRef.resolveSoft(context)
        if resolved:
            # An asset has to be loaded before the entity that consumes it,
            # so the model's assets are queued ahead of the model entity.

            # Animations
            for attr in cast(RW_sf_CreateEntity, resolved).getAttributes(
                "CTFBModel", 3
            ):
                resolved_anim_asset = attr.asTfbRef().resolveSoft(context)
                if resolved_anim_asset is None:
                    continue

                SF_REQUIREMENT_QUEUE.append(resolved_anim_asset)

            # Attached resources (e.g. the .dff mesh and default .anm)
            for attr in cast(RW_sf_CreateEntity, resolved).getAttributes(
                "CSystemCommands", 0
            ):
                resource_guid = Parser(attr.data).readGUID()
                resolved_resource = context.assetByIDSoft(
                    resource_guid
                ) or context.entityByIDSoft(resource_guid)
                if resolved_resource is None:
                    continue

                SF_REQUIREMENT_QUEUE.append(resolved_resource)

            SF_REQUIREMENT_QUEUE.append(resolved)

    if actor.scriptRef:
        resolved = actor.scriptRef.resolveSoft(context)
        if resolved:
            SF_REQUIREMENT_QUEUE.append(resolved)

    # ==========================================

    for req in SF_REQUIREMENT_QUEUE:
        if isinstance(req, RW_sf_CreateEntity):
            if any(req.entityID == e.entityID for e in level.entities()):
                continue  # This entity is already in the level

            _PLACEMENT_COUNT += 1
            level.append(req.duplicate())

        elif isinstance(req, RW_sf_LoadEmbeddedAsset):
            if any(req.guid == e.guid for e in level.embeddedAssets()):
                continue  # This asset is already in the level

            _PLACEMENT_COUNT += 1
            level.append(req.duplicate())

        else:
            print(req.__class__.__name__)
            raise TypeError(
                "We queued a stream func which isnt handled, this should NOT happen, huh"
            )

    # ==========================================

    if any(actor.entityID == e.entityID for e in level.entities()):
        return None

    # The actor goes in BEFORE its script is walked. Scripts reference actors that
    # reference back (banquet's WhackAMole_Mole <-> WhackAMole_Director), and the
    # recursion below guards against cycles by asking whether an entity is already
    # in the level. Appending after the walk would make that guard always false for
    # the actor we are currently walking, and mutual references recurse forever.
    _PLACEMENT_COUNT += 1
    level.append(actor)

    if actor.scriptRef:
        resolved = actor.scriptRef.resolveSoft(context)
        if resolved and isinstance(resolved, RW_sf_LoadEmbeddedAsset):
            breader = TFBScriptBinaryReader(resolved.data, True)
            script = ScriptFile.read(breader)

            for entry in script.global_refs.entries:
                if (
                    entry.category == "user"
                    or entry.string in KNOWN_TFBSCRIPT_BUILTIN_GLOBALS
                ):
                    continue

                # ===== Things on LevelHub =====
                if entry.type == "message":
                    print(Fore.RED + f"[PREFAB SYSTEM ERROR] UNHANDLED {entry.name} ({entry.type}), this might be missing from the target level now")

                elif entry.type == "value":
                    print(Fore.RED + f"[PREFAB SYSTEM ERROR] UNHANDLED {entry.name} ({entry.type}), this might be missing from the target level now")
                    continue
                    source_level_hub_entity = context.levelHub()
                    if not source_level_hub_entity:
                        print(Fore.RED + "[PREFAB SYSTEM ERROR] There is no LevelHub in source level but we need one")
                        continue

                    source_level_hub = LevelHub.from_entity(source_level_hub_entity)

                    dest_level_hub_entity = level.levelHub()
                    if not dest_level_hub_entity:
                        print(Fore.RED + "[PREFAB SYSTEM ERROR] There is no LevelHub in destination level but we need one")
                        continue

                    dest_level_hub = LevelHub.from_entity(dest_level_hub_entity)

                    # ---

                    for var_attr in source_level_hub.getGlobalVariableAttributes():
                        if var_attr.asTfbVariableCommand()[2] == entry.name:
                            print(var_attr.asTfbVariableCommand())
                        print(var_attr.asTfbVariableCommand())
                    
                    #var_attr_to_copy = next(iter(), None)

                    #if any(req.entityID == e.entityID for e in level.entities()):
                    
                elif entry.category == "set": # This has to be a global variable
                    print(Fore.RED + f"[PREFAB SYSTEM ERROR] UNHANDLED {entry.name} (set of {entry.type}), this might be missing from the target level now")

                # ===== Entities and their Assets =====
                elif entry.type == "actor":
                    resolved_actor = context.entityByNameAndBehaviorSoft(
                        entry.name, "CProtoActor"
                    )
                    if resolved_actor is None:
                        print(
                            "[PREFAB SYSTEM] Skipping actor reference: a script referenced by this prefab placement points to an actor that could not be resolved. Reference: "
                            + entry.string
                        )
                        continue

                    if level.entityByIDSoft(resolved_actor.entityID):
                        continue # SUPER SUPER SUPER RARE CASE

                    add_actor_from_level_to_level(
                        CProtoActor.from_entity(resolved_actor), context, level
                    )

                elif entry.type == "camera":
                    resolved_camera = context.entityByNameAndBehaviorSoft(
                        entry.name, "CameraData"
                    )
                    if resolved_camera is None:
                        print(
                            "[PREFAB SYSTEM] Skipping camera reference: a script referenced by this prefab placement points to a camera that could not be resolved. Reference: "
                            + entry.string
                        )
                        continue

                    if level.entityByIDSoft(resolved_camera.entityID):
                        continue # SUPER SUPER SUPER RARE CASE

                    if level.entityByNameAndBehaviorSoft(
                        resolved_camera.tfbGetName(), "CameraData"
                    ):
                        # PRAY THEY ARE SIMILAR ENOUGH LMAO
                        # TODO: Maybe not pray (:
                        pass
                    else:
                        _PLACEMENT_COUNT += 1
                        level.append(resolved_camera.duplicate())

                elif entry.type == "controller":
                    # Should not need any handling
                    # i think all entries are actually built in, just pray again
                    # this is just here as a failsafe if the ::controller was not in KNOWN_TFBSCRIPT_BUILTIN_GLOBALS
                    pass

                elif entry.type == "sound":
                    resolved_sound = context.entityByNameAndBehaviorSoft(
                        entry.name, "CTFBSound"
                    )
                    if resolved_sound is None:
                        print(
                            "[PREFAB SYSTEM] Skipping sound reference: a script referenced by this prefab placement points to a sound that could not be resolved. Reference: "
                            + entry.string
                        )
                        continue

                    if level.entityByIDSoft(resolved_sound.entityID):
                        continue # SUPER SUPER SUPER RARE CASE

                    if level.entityByNameAndBehaviorSoft(
                        resolved_sound.tfbGetName(), "CTFBSound"
                    ):
                        # PRAY THEY ARE SIMILAR ENOUGH LMAO
                        # TODO: Maybe not pray
                        pass
                    else:
                        _PLACEMENT_COUNT += 1
                        level.append(resolved_sound.duplicate())

                elif entry.type == "sprite":
                    resolved_sprite = context.entityByNameAndBehaviorSoft(
                        entry.name, "SpriteObject"
                    )
                    if resolved_sprite is None:
                        print(
                            "[PREFAB SYSTEM] Skipping sprite reference: a script referenced by this prefab placement points to a sprite that could not be resolved. Reference: "
                            + entry.string
                        )
                        continue

                    if level.entityByIDSoft(resolved_sprite.entityID):
                        continue # SUPER SUPER SUPER RARE CASE

                    if level.entityByNameAndBehaviorSoft(
                        resolved_sprite.tfbGetName(), "SpriteObject"
                    ):
                        # PRAY THEY ARE SIMILAR ENOUGH LMAO
                        # TODO: Maybe not pray (:
                        pass
                    else:
                        _PLACEMENT_COUNT += 1
                        level.append(resolved_sprite.duplicate())

    return actor


@dataclass
class Prefab:
    """
    ## Prefabs
    ### What is a prefab?
    A prefab is generated from an existing entity and basically acts like a template.
    You can create a prefab and place multiple instances.
    Prefabs also automatically try to add all referenced, needed (missing) assets to the level

    ### Downsides
    - It maybe adds extra unneeded assets or doesnt accurately link existing assets to the entity, sorry
    - We add things based on if the already is one with the NAME, content may vary

    ### How do i create one?
    Look at the `Prefab.create` method

    ### How do i place one?
    Place your prefab with `my_prefab.place(level)`, `my_prefab` being your prefab and `level` being the level it should be placed in

    All needed assets should be added automatically, if not TELL ME

    ### What doesnt it do?
    - It DOESN´T run the level verify
    - It DOESN´T update placement new in the destination level
       (You gonna have to do that)
    - It DOESN´T bake a batch of cookies for you

    ### Where is the name from?
    Prefab is an actual english word, short for "prefabricated", it means building the parts needed to build something big off site (example: in a factory) before being transported for assembly.
    The word comes from `pre-` (meaning before) and `fabricated` (meaning to build or make).
    The term became popular after WWII when goverments (esp. the UK) rapidly mass produced thousands of small prefab houses to solve housing shortages after the Blitz.

    Sorry for the history lesson, have fun with modding!

    ~ Max
    """

    actor: CProtoActor
    context: RW_StreamFile

    @classmethod
    def create(
        cls, actor: CProtoActor | RW_sf_CreateEntity, level: RW_StreamFile
    ) -> "Prefab":
        """## Creating A Prefab
        Arguments:
            - `actor`: The actor the prefab is based on
            - `level`: The level the actor lives in (or were its resources are)

        Returns:
            - `Prefab`: The created prefab

        Raises:
            - ´ValueError´: Tried to create a prefab with a non CProtoActor entity

        For more info hover over the `Prefab` class
        """

        if actor.behaviour != "CProtoActor":
            raise ValueError(
                "Trying to create a prefab with a non CProtoActor is not possible, you passed an entity with the behavior: "
                + actor.behaviour
                + "\nThis can happen when you fetch an entity by its name but there are multiple entites with that name, try finding by name and behavior"
            )

        return cls(actor=CProtoActor.from_entity(actor), context=level)

    def place(self, level: RW_StreamFile) -> RW_sf_CreateEntity:
        """## Placing a Prefab
        Arguments:
            - `level`: The level the prefab should be placed in

        Returns:
            - `RW_sf_CreateEntity`: The created entity

        Raises:
            - `TypeError`: Invalid stream func when handleing a referenced queued sf, probably not your error, please report if you encounter

        For more info hover over the `Prefab` class
        """

        global _PLACEMENT_COUNT
        _PLACEMENT_COUNT = 0

        new_actor = self.actor.duplicate()

        # === Create a new identity for the copy ===
        new_actor.setRandomEntityId()

        new_name = find_unique_name(level, new_actor.tfbGetName())
        new_actor.tfbSetName(new_name)
        # ========================================

        add_actor_from_level_to_level(new_actor, self.context, level)

        #print(f"[PREFAB SYSTEM] Added {_PLACEMENT_COUNT} streamfuncs to the level while placing a prefab")
        return new_actor
