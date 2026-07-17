from formats.lib.rw_basics import RW_Section, RW_StreamFunc_NotImplemented
from formats.lib.rwConstants import strfunc_func

from formats.streamfuncs.stringfuncs.sf_EnableDirectorsCamera import RW_sf_EnableDirectorsCamera
from formats.streamfuncs.stringfuncs.sf_PlacementNew import RW_sf_PlacementNew
from formats.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import RW_sf_LoadEmbeddedAsset
from formats.streamfuncs.stringfuncs.sf_CreateEntity import RW_sf_CreateEntity
from formats.streamfuncs.stringfuncs.sf_SetFrozenMode import RW_sf_SetFrozenMode
from formats.streamfuncs.stringfuncs.sf_SetRunningMode import RW_sf_SetRunningMode
from formats.streamfuncs.stringfuncs.sf_Shutdown import RW_sf_Shutdown
from formats.streamfuncs.stringfuncs.sf_StartSystem import RW_sf_StartSystem
from formats.streamfuncs.stringfuncs.sf_StopSystem import RW_sf_StopSystem
from formats.streamfuncs.stringfuncs.sf_SetDirectorsCameraMatrix import RW_sf_SetDirectorsCameraMatrix




# fmt: off
STRFUNC_REGISTRY: dict[int, RW_Section] = {
    strfunc_func.sf_PlacementNew.value: RW_sf_PlacementNew,
    strfunc_func.sf_LoadEmbeddedAsset.value: RW_sf_LoadEmbeddedAsset,
    strfunc_func.sf_CreateEntity.value: RW_sf_CreateEntity,
    strfunc_func.sf_SetFrozenMode.value: RW_sf_SetFrozenMode,
    strfunc_func.sf_SetRunningMode.value: RW_sf_SetRunningMode,
    strfunc_func.sf_Shutdown.value: RW_sf_Shutdown,
    strfunc_func.sf_StopSystem.value: RW_sf_StopSystem,
    strfunc_func.sf_StartSystem.value: RW_sf_StartSystem,
    strfunc_func.sf_EnableDirectorsCamera.value: RW_sf_EnableDirectorsCamera,
    strfunc_func.sf_SetDirectorsCameraMatrix.value: RW_sf_SetDirectorsCameraMatrix,
    strfunc_func.sf_Initialize.value: RW_StreamFunc_NotImplemented,
    strfunc_func.sf_DisableDirectorsCamera.value: RW_StreamFunc_NotImplemented,
    strfunc_func.sf_VersionNumber.value: RW_StreamFunc_NotImplemented,
}
# fmt: on

__all__ = [
    "SECTION_REGISTRY",
    "RW_sf_PlacementNew",
    "RW_sf_LoadEmbeddedAsset",
    "RW_sf_CreateEntity",
    "RW_sf_SetFrozenMode",
    "RW_sf_SetRunningMode",
    "RW_sf_Shutdown",
    "RW_sf_StopSystem",
    "RW_sf_StartSystem",
    "RW_sf_EnableDirectorsCamera",
    "RW_sf_SetDirectorsCameraMatrix"
]
