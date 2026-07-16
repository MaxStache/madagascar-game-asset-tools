from formats.lib.rw_basics import RW_Section
from formats.lib.rwConstants import strfunc_func

from formats.streamfuncs.stringfuncs.sf_PlacementNew import RW_sf_PlacementNew
from formats.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import RW_sf_LoadEmbeddedAsset
from formats.streamfuncs.stringfuncs.sf_CreateEntity import RW_sf_CreateEntity


# fmt: off
STRFUNC_REGISTRY: dict[int, RW_Section] = {
    strfunc_func.sf_PlacementNew.value: RW_sf_PlacementNew,
    strfunc_func.sf_LoadEmbeddedAsset.value: RW_sf_LoadEmbeddedAsset,
    strfunc_func.sf_CreateEntity.value: RW_sf_CreateEntity,
}
# fmt: on

__all__ = [
    "SECTION_REGISTRY",
    "RW_sf_PlacementNew",
    "RW_sf_LoadEmbeddedAsset",
]
