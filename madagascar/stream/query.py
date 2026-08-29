"""Read only lookups over the chunk list of a stream file."""

import uuid
from collections.abc import Iterator
from typing import TypeVar

from madagascar.lib.rw_basics import RW_StreamFunc
from madagascar.streamfuncs.stringfuncs.sf_CreateEntity import RW_sf_CreateEntity
from madagascar.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import (
    RW_sf_LoadEmbeddedAsset,
)
from madagascar.streamfuncs.stringfuncs.sf_PlacementNew import RW_sf_PlacementNew

T = TypeVar("T", bound=RW_StreamFunc)


def _require[T: RW_StreamFunc](found: T | None, missing: str) -> T:
    """Unwrap the result of a `...Soft` lookup, or raise `missing`."""
    if found is None:
        raise AssertionError(missing)
    return found


def entityName(entity: RW_sf_CreateEntity) -> str | None:
    """`tfbGetName()`, or None for entities that carry no CTFBCommand name."""
    if not entity.hasAttribute("CTFBCommand", 0x0):
        return None
    return entity.tfbGetName()


class StreamQueryMixin:
    """Lookup helpers mixed into `RW_StreamFile`."""

    contents: list[RW_StreamFunc]

    # region === Generic ===

    def _records(self, kind: type[T]) -> Iterator[T]:
        """Every record of `kind`, in stream order."""
        return (sec for sec in self.contents if isinstance(sec, kind))

    def _entitiesWhere(
        self,
        name: str | None = None,
        behavior: str | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Iterator[RW_sf_CreateEntity]:
        """Entities matching every filter that is not None, in stream order."""
        for entity in self._records(RW_sf_CreateEntity):
            if entity_id is not None and entity.entityID != entity_id:
                continue
            if behavior is not None and entity.behaviour != behavior:
                continue
            if name is not None and entityName(entity) != name:
                continue
            yield entity

    def _assetsWhere(
        self,
        name: str | None = None,
        guid: uuid.UUID | None = None,
    ) -> Iterator[RW_sf_LoadEmbeddedAsset]:
        """Embedded assets matching every filter that is not None, in stream order."""
        for asset in self._records(RW_sf_LoadEmbeddedAsset):
            if guid is not None and asset.guid != guid:
                continue
            if name is not None and asset.name != name:
                continue
            yield asset

    # endregion

    # region === Entities ===

    def entities(self) -> list[RW_sf_CreateEntity]:
        """Every sf_CreateEntity record, in stream order."""
        return list(self._entitiesWhere())

    def entitiesByName(self, name: str) -> list[RW_sf_CreateEntity]:
        """Every sf_CreateEntity record with a specific name, in stream order."""
        return list(self._entitiesWhere(name=name))

    def entitiesByBehavior(self, behavior: str) -> list[RW_sf_CreateEntity]:
        """Every sf_CreateEntity record with a specific behaviour, in stream order."""
        return list(self._entitiesWhere(behavior=behavior))

    def entitiesByNameAndBehavior(
        self, name: str, behavior: str
    ) -> list[RW_sf_CreateEntity]:
        """Every sf_CreateEntity record with a specific name and behaviour, in stream order."""
        return list(self._entitiesWhere(name=name, behavior=behavior))

    def entityByNameSoft(self, name: str) -> RW_sf_CreateEntity | None:
        """Find an entity by TFB object name, or None when nothing matches."""
        return next(self._entitiesWhere(name=name), None)

    def entityByName(self, name: str) -> RW_sf_CreateEntity:
        """Like `entityByNameSoft`, but raises when nothing matches."""
        return _require(
            self.entityByNameSoft(name),
            f"No entity in this stream is named: {name}",
        )

    def entityByNameAndBehaviorSoft(
        self, name: str, behavior: str
    ) -> RW_sf_CreateEntity | None:
        """Find an entity by TFB object name and behaviour, or None."""
        return next(self._entitiesWhere(name=name, behavior=behavior), None)

    def entityByNameAndBehavior(self, name: str, behavior: str) -> RW_sf_CreateEntity:
        """Like `entityByNameAndBehaviorSoft`, but raises when nothing matches."""
        return _require(
            self.entityByNameAndBehaviorSoft(name, behavior),
            f"No entity in this stream is named: {name} with behavior {behavior}",
        )

    def entityByIDSoft(self, entity_id: uuid.UUID | str) -> RW_sf_CreateEntity | None:
        """Find an entity by ID, or None when nothing matches."""
        if isinstance(entity_id, str):
            entity_id = uuid.UUID(entity_id)
        return next(self._entitiesWhere(entity_id=entity_id), None)

    def entityByID(self, entity_id: uuid.UUID | str) -> RW_sf_CreateEntity:
        """Like `entityByIDSoft`, but raises when nothing matches."""
        return _require(
            self.entityByIDSoft(entity_id),
            f"No entity in this stream with id: {entity_id}",
        )

    # endregion

    # region === Embedded assets ===

    def embeddedAssets(self) -> list[RW_sf_LoadEmbeddedAsset]:
        """Every sf_LoadEmbeddedAsset record, in stream order."""
        return list(self._assetsWhere())

    def assetsByName(self, name: str) -> list[RW_sf_LoadEmbeddedAsset]:
        """Every sf_LoadEmbeddedAsset record with a specific name, in stream order."""
        return list(self._assetsWhere(name=name))

    def assetByNameSoft(self, name: str) -> RW_sf_LoadEmbeddedAsset | None:
        """Find an asset by name, or None when nothing matches."""
        return next(self._assetsWhere(name=name), None)

    def assetByName(self, name: str) -> RW_sf_LoadEmbeddedAsset:
        """Like `assetByNameSoft`, but raises when nothing matches.

        Note that multiple assets can share the same name!
        """
        return _require(
            self.assetByNameSoft(name),
            f"No asset in this stream is named: {name}",
        )

    def assetByIDSoft(self, asset_id: uuid.UUID | str) -> RW_sf_LoadEmbeddedAsset | None:
        """Find an asset by ID, or None when nothing matches."""
        if isinstance(asset_id, str):
            asset_id = uuid.UUID(asset_id)

        return next(self._assetsWhere(guid=asset_id), None)

    def assetByID(self, asset_id: uuid.UUID | str) -> RW_sf_LoadEmbeddedAsset:
        """Like `assetByIDSoft`, but raises when nothing matches."""
        return _require(
            self.assetByIDSoft(asset_id),
            f"No asset in this stream with id: {asset_id}",
        )

    # endregion

    # region === Other records ===

    def placementNew(self) -> RW_sf_PlacementNew | None:
        """The sf_PlacementNew record, or None when the stream has none."""
        return next(self._records(RW_sf_PlacementNew), None)

    # endregion
