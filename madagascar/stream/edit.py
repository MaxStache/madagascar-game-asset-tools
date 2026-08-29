"""Mutations of the chunk list, and the consistency checks that guard them."""

import uuid

from madagascar.lib.rw_basics import RW_StreamFunc
from madagascar.stream.query import StreamQueryMixin, entityName
from colorama import Fore, init

init(autoreset=True)


class StreamEditMixin(StreamQueryMixin):
    """Chunk list editing mixed into `RW_StreamFile`."""

    contents: list[RW_StreamFunc]

    def append(self, sf: RW_StreamFunc) -> None:
        self.contents.append(sf)

    def insertAfter(self, reference: RW_StreamFunc, sf: RW_StreamFunc) -> int:
        """Insert `sf` directly after `reference` in the chunk list."""
        for i, sec in enumerate(self.contents):
            if sec is reference:
                self.contents.insert(i + 1, sf)
                return i + 1
        raise ValueError("reference section is not part of this stream")

    def remove(self, sf: RW_StreamFunc) -> int:
        """Remove `sf` from the chunk list. Returns the index it occupied."""
        for i, sec in enumerate(self.contents):
            if sec is sf:
                del self.contents[i]
                return i
        raise ValueError("section is not part of this stream")

    def updatePlacementNew(self, headroom: int = 0) -> None:
        """Rebuilds the sf_PlacementNew section in a stream"""
        placement_new = self.placementNew()

        if placement_new is None:
            raise ValueError("Stream has no sf_PlacementNew section to update")

        counts: dict[str, int] = {}

        for entity in self.entities():
            counts[entity.behaviour] = counts.get(entity.behaviour, 0) + 1

        placement_new.entries = [
            (behaviour, count + headroom) for behaviour, count in counts.items()
        ]

        placement_new.entry_count = len(placement_new.entries)

    def verify(self) -> None:
        """Some simple checks to catch errors before the game crashes (;"""
        print("[STREAM VERIFY] Check started")

        # region === Duplicate Entity IDs and Names ===
        used_entity_ids: set[uuid.UUID] = set()
        used_entity_names: set[str] = set()
        duplicate_names: set[str] = set()

        for entity in self.entities():
            if entity.entityID in used_entity_ids:
                raise ValueError(
                    f"[STREAM VERIFY, SVE001] Duplicate entity ID: {entity.entityID}"
                )
            used_entity_ids.add(entity.entityID)

            name = entityName(entity)
            if name is None:
                continue

            if name in used_entity_names:
                duplicate_names.add(name)
            used_entity_names.add(name)

        if duplicate_names:
            shown = ", ".join(sorted(duplicate_names))
            print(
                Fore.YELLOW
                + f"[STREAM VERIFY, SVE002] Warning: {len(duplicate_names)} "
                + f"duplicate entity name(s): {shown}. \nThis is usually fine and doesnt cause a crash but is very bad practice. It is fine if the name only repeats on one CTFBModel and a CProtoActor. \n"
            )
        # endregion

        # region === Duplicate Asset IDs ===
        used_asset_guids: set[uuid.UUID] = set()
        for asset in self.embeddedAssets():
            if asset.guid in used_asset_guids:
                raise ValueError(
                    "[STREAM VERIFY, SVE003] Duplicate embedded asset GUID: "
                    + f"{asset.guid} ({asset.name})"
                )
            used_asset_guids.add(asset.guid)
        # endregion

        # region === Missing SCRIPT and CTFBModel references by CProtoActors ===
        for actor in self.entitiesByBehavior("CProtoActor"):
            # == MODEL ==
            if actor.hasAttribute("CProtoActor", 2):
                model_ref = actor.getAttribute("CProtoActor", 2).asTfbRef()
                if model_ref.resolveSoft(self) is None:
                    raise ValueError(
                        "[STREAM VERIFY, SVEREF01] Missing model entity with GUID: "
                        + f"{model_ref.guid} ( referenced by {actor.tfbGetName()} ) While this may not cause a crash it is undefined behavior and should be fixed!"
                    )

            # == SCRIPT ==
            if actor.hasAttribute("CProtoActor", 3):
                script_ref = actor.getAttribute("CProtoActor", 3).asTfbRef()
                if script_ref.resolveSoft(self) is None:
                    print(
                        Fore.YELLOW
                        + "[STREAM VERIFY, SVEREF02] WARNING: Missing script asset with GUID: "
                        + f"{script_ref.guid} ( referenced by {actor.tfbGetName()} ) While this may not cause a crash it is bad practice and should be fixed!"
                    )
        # endregion

        # region === Missing  references by CTFBModels ===
        for model in self.entitiesByBehavior(behavior="CTFBModel"):
            # == ANIMATION SLOTS ==
            for attr in model.getAttributes("CTFBModel", 3):
                anim_ref = attr.asTfbRef()
                if anim_ref.resolveSoft(self) is None:
                    raise ValueError(
                        "[STREAM VERIFY, SVEREF03] CTFBModel - Missing animation asset with GUID: "
                        + f"{anim_ref.guid} ( referenced by CTFBModel: {model.tfbGetName()} )"
                    )
            # == VISME ANIMATION SLOTS ==
            for attr in model.getAttributes("CTFBModel", 6):
                anim_ref = attr.asTfbRef()
                if anim_ref.resolveSoft(self) is None:
                    raise ValueError(
                        "[STREAM VERIFY, SVEREF03] CTFBModel - Missing visme animation asset with GUID: "
                        + f"{anim_ref.guid} ( referenced by CTFBModel: {model.tfbGetName()} )"
                    )
                
        # endregion

        print("[STREAM VERIFY] Check finished")
