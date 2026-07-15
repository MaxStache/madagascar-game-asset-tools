try:
    from formats.lib.rw_basics import RW_Section
    from formats.lib.rwConstants import strfunc_func
except ImportError:
    from formats.lib.rw_basics import RW_Section
    from formats.lib.rwConstants import strfunc_func

from formats.stream.RIGHTTORENDER_001F import RW_RightToRender


# fmt: off
STRFUNC_REGISTRY: dict[int, RW_Section] = {
    strfunc_func.sf_VersionNumber.value             : RW_sf_VersionNumber_M1,
}
# fmt: on

__all__ = [
    "SECTION_REGISTRY",
    "RW_TextureDictionary",
]
