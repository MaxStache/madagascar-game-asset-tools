"""Consistency checks run by `RW_StreamFile.verify` before a stream is saved."""

from __future__ import annotations

import math
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

from madformats.lib.parser import Parser
from madformats.stream.query import entityName

from madformats.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import (
    RW_sf_LoadEmbeddedAsset,
)
from tfbscript.script import ScriptFile

if TYPE_CHECKING:
    from madformats.stream.file import RW_StreamFile

# A stage raises ValueError on errors and returns its warnings ("CODE: message").
StreamVerifyStage = Callable[["RW_StreamFile", bool], list[str]]

STREAM_VERIFY_STAGES: list[tuple[str, StreamVerifyStage]] = []


def stream_verification_handler(
    name: str,
) -> Callable[[StreamVerifyStage], StreamVerifyStage]:
    """Register a function as a `verify` stage, run in definition order."""

    def decorator(func: StreamVerifyStage) -> StreamVerifyStage:
        STREAM_VERIFY_STAGES.append((name, func))
        return func

    return decorator


@stream_verification_handler("Entity IDs and Names")
def _stream_verify_entities(stream: RW_StreamFile, verbose: bool = False) -> list[str]:
    warns: list[str] = []
    used_entity_ids: set[uuid.UUID] = set()
    name_types: dict[str, list[str]] = {}

    for entity in stream.entities():
        if entity.entityID in used_entity_ids:
            raise ValueError(
                f"[STREAM VERIFY, SVE001] Duplicate entity ID: {entity.entityID}"
            )
        used_entity_ids.add(entity.entityID)

        name = entityName(entity)
        if name is None:
            continue

        name_types.setdefault(name, []).append(entity.behaviour)

    # Sharing a name between a CTFBModel and a CProtoActor is fine, two CProtoActors is not
    proto_dupes = {
        n for n, types in name_types.items() if types.count("CProtoActor") > 1
    }
    if proto_dupes:
        raise ValueError(
            f"[STREAM VERIFY, SVE003] {len(proto_dupes)} name(s) used by multiple CProtoActors: "
            + ", ".join(sorted(proto_dupes))
        )

    duplicate_names = {n for n, types in name_types.items() if len(types) > 1}

    if verbose and duplicate_names:
        shown = ", ".join(sorted(duplicate_names))

        warns.append(
            f"SVE002: {len(duplicate_names)} duplicate entity name(s): {shown}. "
            + "This can cause unknown behavior, actors that share names may not be properly referenceable in scripts."
        )

    return warns


@stream_verification_handler("Scripts")
def _stream_verify_scripts(stream: RW_StreamFile, verbose: bool = False) -> list[str]:
    scripts: list[RW_sf_LoadEmbeddedAsset] = stream.assetsByType("SCRIPT")

    # Limit 1: Max 800 scripts
    if len(scripts) > 800:
        raise ValueError(
            "[STREAM VERIFY, SVESL01] More than 800 script files loaded: "
            + f"{len(scripts)} scripts registered ( Max is 800, {len(scripts) - 800} too many )"
        )

    for script in stream.scripts():
        parser = Parser(script.data)
        scr = ScriptFile.read(parser)

        if scr.local_refs.entries[-1].string != "my::actor":
            raise ValueError(
                "[STREAM VERIFY, SVESL02] Script´s local table doesn´t end with 'my::actor': "
                + f"{script.name}, last entry is: {scr.local_refs.entries[-1].string}"
            )

    return []


@stream_verification_handler("CProtoActor References")
def _stream_verify_proto_actor_refs(
    stream: RW_StreamFile, verbose: bool = False
) -> list[str]:
    warns: list[str] = []
    for actor in stream.entitiesByBehavior("CProtoActor"):
        # == MODEL ==
        if actor.hasAttribute("CProtoActor", 2):
            model_ref = actor.getAttribute("CProtoActor", 2).asTfbRef()
            if model_ref.resolveSoft(stream) is None:
                raise ValueError(
                    "[STREAM VERIFY, SVEREF01] Missing model entity with GUID: "
                    + f"{model_ref.guid} ( referenced by {actor.tfbGetName()} ) While this may not cause a crash it is undefined behavior and should be fixed!"
                )

        # == SCRIPT ==
        if actor.hasAttribute("CProtoActor", 3):
            script_ref = actor.getAttribute("CProtoActor", 3).asTfbRef()
            if script_ref.resolveSoft(stream) is None:
                warns.append(
                    "SVEREF02: Missing script asset with GUID: "
                    + f"{script_ref.guid} ( referenced by {actor.tfbGetName()} ) While this may not cause a crash it is bad practice and should be fixed!"
                )

    return warns


@stream_verification_handler("CTFBModel References")
def _stream_verify_tfb_model_refs(
    stream: RW_StreamFile, verbose: bool = False
) -> list[str]:
    for model in stream.entitiesByBehavior(behavior="CTFBModel"):
        # == ANIMATION SLOTS ==
        for attr in model.getAttributes("CTFBModel", 3):
            anim_ref = attr.asTfbRef()
            if anim_ref.resolveSoft(stream) is None:
                raise ValueError(
                    "[STREAM VERIFY, SVEREF03] CTFBModel - Missing animation asset with GUID: "
                    + f"{anim_ref.guid} ( referenced by CTFBModel: {model.tfbGetName()} )"
                )
        # == VISME ANIMATION SLOTS ==
        for attr in model.getAttributes("CTFBModel", 6):
            anim_ref = attr.asTfbRef()
            if anim_ref.resolveSoft(stream) is None:
                raise ValueError(
                    "[STREAM VERIFY, SVEREF03] CTFBModel - Missing visme animation asset with GUID: "
                    + f"{anim_ref.guid} ( referenced by CTFBModel: {model.tfbGetName()} )"
                )

    return []


@stream_verification_handler("Asset IDs")
def _stream_verify_asset_ids(stream: RW_StreamFile, verbose: bool = False) -> list[str]:
    used_asset_ids: set[uuid.UUID] = set()

    for asset in stream.embeddedAssets():
        if asset.guid in used_asset_ids:
            raise ValueError(f"[STREAM VERIFY] Duplicate asset ID: {asset.guid}")
        used_asset_ids.add(asset.guid)

    return []


@stream_verification_handler("General")
def _stream_verify_general(stream: RW_StreamFile, verbose: bool = False) -> list[str]:

    for entity in stream.entities():
        if not entity.hasTransform():
            continue

        m = entity.getMatrix()
        if not all(math.isfinite(v) for row in m for v in row):
            raise ValueError(
                "[STREAM VERIFY, SVEG01] Non-finite transform (NaN/Inf) on entity: "
                + entity.getDisplayName()
            )

    return []
