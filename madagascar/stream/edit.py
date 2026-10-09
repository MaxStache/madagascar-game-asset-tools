"""Mutations of the chunk list, and the consistency checks that guard them."""

import uuid

from madagascar.lib.rw_basics import RW_StreamFunc
from madagascar.stream.query import StreamQueryMixin, entityName
from colorama import Fore, init

from madagascar.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import (
    RW_sf_LoadEmbeddedAsset,
)

init(autoreset=True)

class StreamEditMixin(StreamQueryMixin):
    """Chunk list editing mixed into `RW_StreamFile`."""

    contents: list[RW_StreamFunc]

    def append(self, content: RW_StreamFunc | list[RW_StreamFunc]) -> None:
        items = content if isinstance(content, list) else [content]

        self.contents.extend(items)

        self._INTERNAL_CHECKING_PLACEMENT_DIRTY = True

    def insertAfter(self, reference: RW_StreamFunc, content: RW_StreamFunc) -> int:
        """Insert `content` directly after `reference` in the chunk list."""
        try:
            index = self.contents.index(reference)
        except ValueError:
            raise ValueError("reference section is not part of this stream") from None

        self.contents.insert(index + 1, content)
        self._INTERNAL_CHECKING_PLACEMENT_DIRTY = True

        return index + 1

    def remove(self, sf: RW_StreamFunc) -> int:
        """Remove `sf` from the chunk list. Returns the index it occupied."""
        for i, sec in enumerate(self.contents):
            if sec is sf:
                del self.contents[i]
                self._INTERNAL_CHECKING_PLACEMENT_DIRTY = True
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

        self._INTERNAL_CHECKING_PLACEMENT_UPDATED = True
        self._INTERNAL_CHECKING_PLACEMENT_DIRTY = False

    def verify(self, verbose: bool = False) -> None:
        """Some simple checks to catch errors before the game crashes (;"""
        print("[STREAM VERIFY] Check started")

        if (
            not self._INTERNAL_CHECKING_PLACEMENT_UPDATED
            and self._INTERNAL_CHECKING_PLACEMENT_DIRTY
        ):
            raise ValueError(
                "[STREAM VERIFY, SPE001] Stream was modified in length but never updated with 'stream.updatePlacementNew()' before verifying and saving, add 'stream.updatePlacementNew()' to resolve this error "
            )

        # region === Duplicate Entity IDs and Names ===
        used_entity_ids: set[uuid.UUID] = set()
        name_types: dict[str, list[str]] = {}

        for entity in self.entities():
            if entity.entityID in used_entity_ids:
                raise ValueError(
                    f"[STREAM VERIFY, SVE001] Duplicate entity ID: {entity.entityID}"
                )
            used_entity_ids.add(entity.entityID)

            name = entityName(entity)
            if name is None:
                continue

            name_types.setdefault(name, []).append(type(entity).__name__)

        duplicate_names = {n for n, types in name_types.items() if len(types) > 1}

        if verbose:
            if duplicate_names:
                shown = ", ".join(sorted(duplicate_names))

                print(
                    Fore.YELLOW
                    + f"[STREAM VERIFY, SVE002] Warning: {len(duplicate_names)} "
                    + f"duplicate entity name(s): \n{shown}. \nThis is usually fine and doesnt cause a crash but is very bad practice. It is fine if the name only repeats on one CTFBModel and a CProtoActor."
                )
        else:
            allowed = ["CProtoActor", "CTFBModel"]
            bad_names = {
                n for n in duplicate_names if sorted(name_types[n]) != allowed
            }

            if bad_names:

                print(
                    Fore.YELLOW
                    + f"[STREAM VERIFY, SVE002] WARN: {len(bad_names)} "
                    + f"duplicate entity name(s): \n{", ".join(bad_names)}"
                )
        # endregion

        # region === Scripting limits ===
        scripts: list[RW_sf_LoadEmbeddedAsset] = self.assetsByType("SCRIPT")

        # Limit 1: Max 800 scripts
        if len(scripts) > 800:
            raise ValueError(
                "[STREAM VERIFY, SVESL01] More than 800 script files loaded: "
            + f"{len(scripts)} scripts registered ( Max is 800, {len(scripts)-800} too many )"
            )
        # ---

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
        print(Fore.GREEN + "[STREAM VERIFY] Check suceeded!")

        self._INTERNAL_CHECKING_VERIFIED = True
