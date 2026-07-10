
try:
    from rw_basics import RW_Section, RW_Section_NotImplemented
    from rwConstants import RWSectionType
except ImportError:
    from formats.rw_basics import RW_Section, RW_Section_NotImplemented
    from formats.rwConstants import RWSectionType

from .STRING_0002 import RW_String
from .TEXTURE_0006 import RW_Texture
from .EXTENSION_0003 import RW_Extension
from .BINMESHPLUGIN_050E import RW_BinMeshPlugin
from .MATERIALEFFECTSPLUGIN_0120 import RW_MaterialEffectsPlugin
from .MATERIAL_0007 import RW_Material
from .RIGHTTORENDER_001F import RW_RightToRender
from .USERDATAPLUGIN_011F import RW_UserDataPlugin
from .HANIMPLUGIN_011E import RW_HAnimPlugin
from .ATOMIC_0014 import RW_Atomic
from .CLUMP_0010 import RW_Clump
from .FRAMELIST_000E import RW_FrameList
from .GEOMETRYLIST_001A import RW_GeometryList
from .GEOMETRY_000F import RW_Geometry
from .MATLIST_0008 import RW_MaterialList
from .CAMERA_0005 import RW_Camera

# SKY (PS2)
from .SKYMIPMAPVAL_0110 import RW_SkyMipmapVal
# ----

from .TFB.UNKNOWN1_800000FE import RW_TFB_UNKNOWN1
from .TFB.UNKNOWN2_800000D4 import RW_TFB_UNKNOWN2
from .TFB.UNKNOWN3_800000F6 import RW_TFB_UNKNOWN3

# fmt: off
SECTION_REGISTRY: dict[int, RW_Section] = {
    RWSectionType.rwID_NAOBJECT.value             : RW_Section_NotImplemented,
    RWSectionType.rwID_STRUCT.value               : RW_Section_NotImplemented,
    RWSectionType.rwID_STRING.value               : RW_String,
    RWSectionType.rwID_EXTENSION.value            : RW_Extension,
    RWSectionType.rwID_CAMERA.value               : RW_Camera,
    RWSectionType.rwID_TEXTURE.value              : RW_Texture,
    RWSectionType.rwID_MATERIAL.value             : RW_Material,
    RWSectionType.rwID_MATLIST.value              : RW_MaterialList,
    RWSectionType.rwID_ATOMICSECT.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_PLANESECT.value            : RW_Section_NotImplemented,
    RWSectionType.rwID_WORLD.value                : RW_Section_NotImplemented,
    RWSectionType.rwID_SPLINE.value               : RW_Section_NotImplemented,
    RWSectionType.rwID_MATRIX.value               : RW_Section_NotImplemented,
    RWSectionType.rwID_FRAMELIST.value            : RW_FrameList,
    RWSectionType.rwID_GEOMETRY.value             : RW_Geometry,
    RWSectionType.rwID_CLUMP.value                : RW_Clump,
    RWSectionType.rwID_LIGHT.value                : RW_Section_NotImplemented,
    RWSectionType.rwID_UNICODESTRING.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_ATOMIC.value               : RW_Atomic,
    RWSectionType.rwID_TEXTURENATIVE.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_TEXDICTIONARY.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_ANIMDATABASE.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_IMAGE.value                : RW_Section_NotImplemented,
    RWSectionType.rwID_SKINANIMATION.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_GEOMETRYLIST.value         : RW_GeometryList,
    RWSectionType.rwID_ANIMANIMATION.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_TEAM.value                 : RW_Section_NotImplemented,
    RWSectionType.rwID_CROWD.value                : RW_Section_NotImplemented,
    RWSectionType.rwID_DMORPHANIMATION.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_RIGHTTORENDER.value        : RW_RightToRender,
    RWSectionType.rwID_MTEFFECTNATIVE.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_MTEFFECTDICT.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_TEAMDICTIONARY.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_PITEXDICTIONARY.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_TOC.value                  : RW_Section_NotImplemented,
    RWSectionType.rwID_PRTSTDGLOBALDATA.value     : RW_Section_NotImplemented,
    RWSectionType.rwID_ALTPIPE.value              : RW_Section_NotImplemented,
    RWSectionType.rwID_PIPEDS.value               : RW_Section_NotImplemented,
    RWSectionType.rwID_PATCHMESH.value            : RW_Section_NotImplemented,
    RWSectionType.rwID_CHUNKGROUPSTART.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_CHUNKGROUPEND.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_UVANIMDICT.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_COLLTREE.value             : RW_Section_NotImplemented,
    RWSectionType.rwID_METRICSPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_SPLINEPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_STEREOPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_VRMLPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_MORPHPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_PVSPLUGIN.value            : RW_Section_NotImplemented,
    RWSectionType.rwID_MEMLEAKPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_ANIMPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_GLOSSPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_LOGOPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_MEMINFOPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_RANDOMPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_PNGIMAGEPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_BONEPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_VRMLANIMPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_SKYMIPMAPVAL.value         : RW_SkyMipmapVal,
    RWSectionType.rwID_MRMPLUGIN.value            : RW_Section_NotImplemented,
    RWSectionType.rwID_LODATMPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_MEPLUGIN.value             : RW_Section_NotImplemented,
    RWSectionType.rwID_LTMAPPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_REFINEPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_SKINPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_LABELPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_PARTICLESPLUGIN.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_GEOMTXPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_SYNTHCOREPLUGIN.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_STQPPPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_PARTPPPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_COLLISPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_HANIMPLUGIN.value          : RW_HAnimPlugin,
    RWSectionType.rwID_USERDATAPLUGIN.value       : RW_UserDataPlugin,
    RWSectionType.rwID_MATERIALEFFECTSPLUGIN.value: RW_MaterialEffectsPlugin,
    RWSectionType.rwID_PARTICLESYSTEMPLUGIN.value : RW_Section_NotImplemented,
    RWSectionType.rwID_DMORPHPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_PATCHPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_TEAMPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_CROWDPPPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_MIPSPLITPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_ANISOTPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_GCNMATPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_GPVSPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_XBOXMATPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_MULTITEXPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_CHAINPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_TOONPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_PTANKPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_PRTSTDPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_PDSPLUGIN.value            : RW_Section_NotImplemented,
    RWSectionType.rwID_PRTADVPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_NORMMAPPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_ADCPLUGIN.value            : RW_Section_NotImplemented,
    RWSectionType.rwID_UVANIMPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_CHARSEPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_NOHSWORLDPLUGIN.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_IMPUTILPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_SLERPPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_OPTIMPLUGIN.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_TLWORLDPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_DATABASEPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_RAYTRACEPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_RAYPLUGIN.value            : RW_Section_NotImplemented,
    RWSectionType.rwID_LIBRARYPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_2DPLUGIN.value             : RW_Section_NotImplemented,
    RWSectionType.rwID_TILERENDPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_JPEGIMAGEPLUGIN.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_TGAIMAGEPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_GIFIMAGEPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_QUATPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_SPLINEPVSPLUGIN.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_MIPMAPPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_MIPMAPKPLUGIN.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_2DFONT.value               : RW_Section_NotImplemented,
    RWSectionType.rwID_INTSECPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_TIFFIMAGEPLUGIN.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_PICKPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_BMPIMAGEPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_RASIMAGEPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_SKINFXPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_VCATPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_2DPATH.value               : RW_Section_NotImplemented,
    RWSectionType.rwID_2DBRUSH.value              : RW_Section_NotImplemented,
    RWSectionType.rwID_2DOBJECT.value             : RW_Section_NotImplemented,
    RWSectionType.rwID_2DSHAPE.value              : RW_Section_NotImplemented,
    RWSectionType.rwID_2DSCENE.value              : RW_Section_NotImplemented,
    RWSectionType.rwID_2DPICKREGION.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_2DOBJECTSTRING.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_2DANIMPLUGIN.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_2DANIM.value               : RW_Section_NotImplemented,
    RWSectionType.rwID_2DKEYFRAME.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_2DMAESTRO.value            : RW_Section_NotImplemented,
    RWSectionType.rwID_BARYCENTRIC.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_PITEXDICTIONARYTK.value    : RW_Section_NotImplemented,
    RWSectionType.rwID_TOCTOOLKIT.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_TPLTOOLKIT.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_ALTPIPETOOLKIT.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_ANIMTOOLKIT.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_SKINSPLITTOOKIT.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_CMPKEYTOOLKIT.value        : RW_Section_NotImplemented,
    RWSectionType.rwID_GEOMCONDPLUGIN.value       : RW_Section_NotImplemented,
    RWSectionType.rwID_WINGPLUGIN.value           : RW_Section_NotImplemented,
    RWSectionType.rwID_GENCPIPETOOLKIT.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_LTMAPCNVTOOLKIT.value      : RW_Section_NotImplemented,
    RWSectionType.rwID_FILESYSTEMPLUGIN.value     : RW_Section_NotImplemented,
    RWSectionType.rwID_DICTTOOLKIT.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_UVANIMLINEAR.value         : RW_Section_NotImplemented,
    RWSectionType.rwID_UVANIMPARAM.value          : RW_Section_NotImplemented,
    RWSectionType.rwID_BINMESHPLUGIN.value        : RW_BinMeshPlugin,
    RWSectionType.rwID_NATIVEDATAPLUGIN.value     : RW_Section_NotImplemented,
    # other
    RWSectionType.rwID_ZModelerLock.value: RW_Section_NotImplemented,
    RWSectionType.rwID_Frame.value       : RW_Section_NotImplemented,


    # TFB - World
    0x800000d4: RW_TFB_UNKNOWN1,
    0x800000fe: RW_TFB_UNKNOWN2,
    0x800000f6: RW_TFB_UNKNOWN3,
}
# fmt: on

__all__ = [
    "SECTION_REGISTRY",
    "RW_String",
    "RW_Texture",
    "RW_Extension",
    "RW_BinMeshPlugin",
    "RW_MaterialEffectsPlugin",
    "RW_UserDataPlugin",
    "RW_SkyMipmapVal",
    "RW_RightToRender",
    "RW_Material",
    "RW_GeometryList",
    "RW_Geometry",
    "RW_MaterialList",
    "RW_Atomic",
    "RW_Camera",
    "RW_Clump",
    "RW_FrameList",
    "RW_TFB_UNKNOWN1",
]
