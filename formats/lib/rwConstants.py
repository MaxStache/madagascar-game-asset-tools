from enum import Enum, IntEnum


def MAKECHUNKID(vId, sId):
    """
    vId = vendorID
    sId = sectionID
    """
    return ((vId & 0xFFFFFF) << 8) | (sId & 0xFF)


class RwVendor(IntEnum):
    # --- RW / Criterion ---
    CORE = 0x000000  # Core engine
    CRITERIONTK = 0x000001  # Toolkit utilities (Rt* libraries).
    REDLINERACER = 0x000002  # Internal Redline Racer module.
    CSLRD = 0x000003
    CRITERIONINT = 0x000004
    CRITERIONWORLD = 0x000005  # World
    BETA = 0x000006
    CRITERIONRM = 0x000007
    CRITERIONRWA = 0x000008  # RW Audio
    CRITERIONRWP = 0x000009  # RW Physics

    # --- Third-Party ---
    ZModeler = 0x0000F2  # ZModeler

    ROCKSTAR = 0x0253F2  # Rockstar Games
    TFB = 0x800000  # Toys for Bob


# fmt: off
class RWSectionType(Enum):
    rwID_NAOBJECT              = MAKECHUNKID(RwVendor.CORE, 0x00)
    rwID_STRUCT                = MAKECHUNKID(RwVendor.CORE, 0x01)
    rwID_STRING                = MAKECHUNKID(RwVendor.CORE, 0x02)
    rwID_EXTENSION             = MAKECHUNKID(RwVendor.CORE, 0x03)
    rwID_CAMERA                = MAKECHUNKID(RwVendor.CORE, 0x05)
    rwID_TEXTURE               = MAKECHUNKID(RwVendor.CORE, 0x06)
    rwID_MATERIAL              = MAKECHUNKID(RwVendor.CORE, 0x07)
    rwID_MATLIST               = MAKECHUNKID(RwVendor.CORE, 0x08)
    rwID_ATOMICSECT            = MAKECHUNKID(RwVendor.CORE, 0x09)
    rwID_PLANESECT             = MAKECHUNKID(RwVendor.CORE, 0x0A)
    rwID_WORLD                 = MAKECHUNKID(RwVendor.CORE, 0x0B)
    rwID_SPLINE                = MAKECHUNKID(RwVendor.CORE, 0x0C)
    rwID_MATRIX                = MAKECHUNKID(RwVendor.CORE, 0x0D)
    rwID_FRAMELIST             = MAKECHUNKID(RwVendor.CORE, 0x0E)
    rwID_GEOMETRY              = MAKECHUNKID(RwVendor.CORE, 0x0F)
    rwID_CLUMP                 = MAKECHUNKID(RwVendor.CORE, 0x10)
    rwID_LIGHT                 = MAKECHUNKID(RwVendor.CORE, 0x12)
    rwID_UNICODESTRING         = MAKECHUNKID(RwVendor.CORE, 0x13)
    rwID_ATOMIC                = MAKECHUNKID(RwVendor.CORE, 0x14)
    rwID_TEXTURENATIVE         = MAKECHUNKID(RwVendor.CORE, 0x15) # also known as Raster
    rwID_TEXDICTIONARY         = MAKECHUNKID(RwVendor.CORE, 0x16)
    rwID_ANIMDATABASE          = MAKECHUNKID(RwVendor.CORE, 0x17)
    rwID_IMAGE                 = MAKECHUNKID(RwVendor.CORE, 0x18)
    rwID_SKINANIMATION         = MAKECHUNKID(RwVendor.CORE, 0x19)
    rwID_GEOMETRYLIST          = MAKECHUNKID(RwVendor.CORE, 0x1A)
    rwID_ANIMANIMATION         = MAKECHUNKID(RwVendor.CORE, 0x1B)
    rwID_TEAM                  = MAKECHUNKID(RwVendor.CORE, 0x1C)
    rwID_CROWD                 = MAKECHUNKID(RwVendor.CORE, 0x1D)
    rwID_DMORPHANIMATION       = MAKECHUNKID(RwVendor.CORE, 0x1E)
    rwID_RIGHTTORENDER         = MAKECHUNKID(RwVendor.CORE, 0x1F)
    rwID_MTEFFECTNATIVE        = MAKECHUNKID(RwVendor.CORE, 0x20)
    rwID_MTEFFECTDICT          = MAKECHUNKID(RwVendor.CORE, 0x21)
    rwID_TEAMDICTIONARY        = MAKECHUNKID(RwVendor.CORE, 0x22)
    rwID_PITEXDICTIONARY       = MAKECHUNKID(RwVendor.CORE, 0x23)
    rwID_TOC                   = MAKECHUNKID(RwVendor.CORE, 0x24)
    rwID_PRTSTDGLOBALDATA      = MAKECHUNKID(RwVendor.CORE, 0x25)
    rwID_ALTPIPE               = MAKECHUNKID(RwVendor.CORE, 0x26)
    rwID_PIPEDS                = MAKECHUNKID(RwVendor.CORE, 0x27)
    rwID_PATCHMESH             = MAKECHUNKID(RwVendor.CORE, 0x28)
    rwID_CHUNKGROUPSTART       = MAKECHUNKID(RwVendor.CORE, 0x29)
    rwID_CHUNKGROUPEND         = MAKECHUNKID(RwVendor.CORE, 0x2A)
    rwID_UVANIMDICT            = MAKECHUNKID(RwVendor.CORE, 0x2B)
    rwID_COLLTREE              = MAKECHUNKID(RwVendor.CORE, 0x2C)
    rwID_METRICSPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x01)
    rwID_SPLINEPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x02)
    rwID_STEREOPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x03)
    rwID_VRMLPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x04)
    rwID_MORPHPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x05)
    rwID_PVSPLUGIN             = MAKECHUNKID(RwVendor.CRITERIONTK, 0x06)
    rwID_MEMLEAKPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x07)
    rwID_ANIMPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x08)
    rwID_GLOSSPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x09)
    rwID_LOGOPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x0A)
    rwID_MEMINFOPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x0B)
    rwID_RANDOMPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x0C)
    rwID_PNGIMAGEPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x0D)
    rwID_BONEPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x0E)
    rwID_VRMLANIMPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x0F)
    rwID_SKYMIPMAPVAL          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x10)
    rwID_MRMPLUGIN             = MAKECHUNKID(RwVendor.CRITERIONTK, 0x11)
    rwID_LODATMPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x12)
    rwID_MEPLUGIN              = MAKECHUNKID(RwVendor.CRITERIONTK, 0x13)
    rwID_LTMAPPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x14)
    rwID_REFINEPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x15)
    rwID_SKINPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x16)
    rwID_LABELPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x17)
    rwID_PARTICLESPLUGIN       = MAKECHUNKID(RwVendor.CRITERIONTK, 0x18)
    rwID_GEOMTXPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x19)
    rwID_SYNTHCOREPLUGIN       = MAKECHUNKID(RwVendor.CRITERIONTK, 0x1A)
    rwID_STQPPPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x1B)
    rwID_PARTPPPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x1C)
    rwID_COLLISPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x1D)
    rwID_HANIMPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x1E)
    rwID_USERDATAPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x1F)
    rwID_MATERIALEFFECTSPLUGIN = MAKECHUNKID(RwVendor.CRITERIONTK, 0x20)
    rwID_PARTICLESYSTEMPLUGIN  = MAKECHUNKID(RwVendor.CRITERIONTK, 0x21)
    rwID_DMORPHPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x22)
    rwID_PATCHPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x23)
    rwID_TEAMPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x24)
    rwID_CROWDPPPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x25)
    rwID_MIPSPLITPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x26)
    rwID_ANISOTPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x27)
    rwID_GCNMATPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x29)
    rwID_GPVSPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x2A)
    rwID_XBOXMATPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x2B)
    rwID_MULTITEXPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x2C)
    rwID_CHAINPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x2D)
    rwID_TOONPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x2E)
    rwID_PTANKPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x2F)
    rwID_PRTSTDPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x30)
    rwID_PDSPLUGIN             = MAKECHUNKID(RwVendor.CRITERIONTK, 0x31)
    rwID_PRTADVPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x32)
    rwID_NORMMAPPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x33)
    rwID_ADCPLUGIN             = MAKECHUNKID(RwVendor.CRITERIONTK, 0x34)
    rwID_UVANIMPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x35)
    rwID_CHARSEPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x80)
    rwID_NOHSWORLDPLUGIN       = MAKECHUNKID(RwVendor.CRITERIONTK, 0x81)
    rwID_IMPUTILPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x82)
    rwID_SLERPPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x83)
    rwID_OPTIMPLUGIN           = MAKECHUNKID(RwVendor.CRITERIONTK, 0x84)
    rwID_TLWORLDPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x85)
    rwID_DATABASEPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x86)
    rwID_RAYTRACEPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x87)
    rwID_RAYPLUGIN             = MAKECHUNKID(RwVendor.CRITERIONTK, 0x88)
    rwID_LIBRARYPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x89)
    rwID_2DPLUGIN              = MAKECHUNKID(RwVendor.CRITERIONTK, 0x90)
    rwID_TILERENDPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x91)
    rwID_JPEGIMAGEPLUGIN       = MAKECHUNKID(RwVendor.CRITERIONTK, 0x92)
    rwID_TGAIMAGEPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x93)
    rwID_GIFIMAGEPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x94)
    rwID_QUATPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x95)
    rwID_SPLINEPVSPLUGIN       = MAKECHUNKID(RwVendor.CRITERIONTK, 0x96)
    rwID_MIPMAPPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x97)
    rwID_MIPMAPKPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONTK, 0x98)
    rwID_2DFONT                = MAKECHUNKID(RwVendor.CRITERIONTK, 0x99)
    rwID_INTSECPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x9A)
    rwID_TIFFIMAGEPLUGIN       = MAKECHUNKID(RwVendor.CRITERIONTK, 0x9B)
    rwID_PICKPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0x9C)
    rwID_BMPIMAGEPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x9D)
    rwID_RASIMAGEPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0x9E)
    rwID_SKINFXPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0x9F)
    rwID_VCATPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA0)
    rwID_2DPATH                = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA1)
    rwID_2DBRUSH               = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA2)
    rwID_2DOBJECT              = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA3)
    rwID_2DSHAPE               = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA4)
    rwID_2DSCENE               = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA5)
    rwID_2DPICKREGION          = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA6)
    rwID_2DOBJECTSTRING        = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA7)
    rwID_2DANIMPLUGIN          = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA8)
    rwID_2DANIM                = MAKECHUNKID(RwVendor.CRITERIONTK, 0xA9)
    rwID_2DKEYFRAME            = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB0)
    rwID_2DMAESTRO             = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB1)
    rwID_BARYCENTRIC           = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB2)
    rwID_PITEXDICTIONARYTK     = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB3)
    rwID_TOCTOOLKIT            = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB4)
    rwID_TPLTOOLKIT            = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB5)
    rwID_ALTPIPETOOLKIT        = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB6)
    rwID_ANIMTOOLKIT           = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB7)
    rwID_SKINSPLITTOOKIT       = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB8)
    rwID_CMPKEYTOOLKIT         = MAKECHUNKID(RwVendor.CRITERIONTK, 0xB9)
    rwID_GEOMCONDPLUGIN        = MAKECHUNKID(RwVendor.CRITERIONTK, 0xBA)
    rwID_WINGPLUGIN            = MAKECHUNKID(RwVendor.CRITERIONTK, 0xBB)
    rwID_GENCPIPETOOLKIT       = MAKECHUNKID(RwVendor.CRITERIONTK, 0xBC)
    rwID_LTMAPCNVTOOLKIT       = MAKECHUNKID(RwVendor.CRITERIONTK, 0xBD)
    rwID_FILESYSTEMPLUGIN      = MAKECHUNKID(RwVendor.CRITERIONTK, 0xBE)
    rwID_DICTTOOLKIT           = MAKECHUNKID(RwVendor.CRITERIONTK, 0xBF)
    rwID_UVANIMLINEAR          = MAKECHUNKID(RwVendor.CRITERIONTK, 0xC0)
    rwID_UVANIMPARAM           = MAKECHUNKID(RwVendor.CRITERIONTK, 0xC1)
    rwID_BINMESHPLUGIN         = MAKECHUNKID(RwVendor.CRITERIONWORLD, 0x0E)
    rwID_NATIVEDATAPLUGIN      = MAKECHUNKID(RwVendor.CRITERIONWORLD, 0x10)

    # ZModeler
    rwID_ZModeler_ZModelerLock = MAKECHUNKID(RwVendor.ZModeler, 0x1E)


    # Rockstar
    rwID_rockstar_Frame              = MAKECHUNKID(RwVendor.ROCKSTAR, 0xFE)
    rwID_rockstar_ReflectionMaterial = MAKECHUNKID(RwVendor.ROCKSTAR, 0xFC)
    rwID_rockstar_SpecularMaterial   = MAKECHUNKID(RwVendor.ROCKSTAR, 0xF6)
    rwID_rockstar_Breakable          = MAKECHUNKID(RwVendor.ROCKSTAR, 0xFD)

    # RW Audio, DAT = DATA, HDR = HEADER
       # single object definition alias
    rwaID_OBJDEFALIAS            = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x00)
    rwaID_OBJDEFALIAS_DATA       = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x01)
       # single wave
    rwaID_WAVE                   = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x02)
    rwaID_WAVESTRUCT             = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x03)
    rwaID_WAVEDATA               = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x04)
       # object dictionary
    rwaID_OBJDICT                = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x05)
    rwaID_OBJDICTOBJDEFALIAS     = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x06)
    rwaID_OBJDICTOBJDEFALIAS_HDR = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x07)
    rwaID_OBJDICTOBJDEFALIAS_DAT = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x08)
       # wave dictionary
    rwaID_WAVEDICT               = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x09)
    rwaID_WAVEDICT_DICT          = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0A)
    rwaID_WAVEDICT_WAVE_HDR      = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0B)
    rwaID_WAVEDICT_WAVE          = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0C)
    rwaID_WAVEDICT_WAVEDATA_HDR  = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0D)
    rwaID_WAVEDICT_WAVEDATA      = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0E)

    # TFB
    rwID_tfb_AtomicSec1 = MAKECHUNKID(RwVendor.TFB, 0xD4)  # found on atomic world sector - 12B
    rwID_tfb_AtomicSec2 = MAKECHUNKID(RwVendor.TFB, 0xFE)  # found on atomic world sector - 16B
    rwID_tfb_World      = MAKECHUNKID(RwVendor.TFB, 0xB0)  # found on world - 16B
    rwID_tfb_Material   = MAKECHUNKID(RwVendor.TFB, 0xF6)  # found on material (in world) - 33B
    rwID_tfb_Atomic1    = MAKECHUNKID(RwVendor.TFB, 0xED)  # found on atomic - 12B
    rwID_tfb_Atomic2    = MAKECHUNKID(RwVendor.TFB, 0xFD)  # found on atomic - 28B
    rwID_tfb_Clump      = MAKECHUNKID(RwVendor.TFB, 0xB1)  # found on clump - 8B
    rwID_tfb_Texture    = MAKECHUNKID(RwVendor.TFB, 0xDD)  # found on TextureNative and Texture - 12B


class strfunc_func(Enum):
    sf_VersionNumber            = MAKECHUNKID(RwVendor.CRITERIONRM, -0x1)
    sf_Reset                    = MAKECHUNKID(RwVendor.CRITERIONRM, 0x00)
    sf_Reserved1                = MAKECHUNKID(RwVendor.CRITERIONRM, 0x01)
    sf_Reserved2                = MAKECHUNKID(RwVendor.CRITERIONRM, 0x02)
    sf_SetDirectorsCameraMatrix = MAKECHUNKID(RwVendor.CRITERIONRM, 0x03)
    sf_CreateEntity             = MAKECHUNKID(RwVendor.CRITERIONRM, 0x04)
    sf_UpdateEntityAttributes   = MAKECHUNKID(RwVendor.CRITERIONRM, 0x05)
    sf_SetFrozenMode            = MAKECHUNKID(RwVendor.CRITERIONRM, 0x06) # pause game
    sf_SetRunningMode           = MAKECHUNKID(RwVendor.CRITERIONRM, 0x07) # unpause game
    sf_EnableDirectorsCamera    = MAKECHUNKID(RwVendor.CRITERIONRM, 0x08)
    sf_DisableDirectorsCamera   = MAKECHUNKID(RwVendor.CRITERIONRM, 0x09)
    sf_TextComment              = MAKECHUNKID(RwVendor.CRITERIONRM, 0x0A)
    sf_StartSystem              = MAKECHUNKID(RwVendor.CRITERIONRM, 0x0B)
    sf_StopSystem               = MAKECHUNKID(RwVendor.CRITERIONRM, 0x0C)
    sf_DeleteEntity             = MAKECHUNKID(RwVendor.CRITERIONRM, 0x0D)
    sf_DeleteAllEntities        = MAKECHUNKID(RwVendor.CRITERIONRM, 0x0E)
    sf_UnLoadAsset              = MAKECHUNKID(RwVendor.CRITERIONRM, 0x0F)
    sf_Shutdown                 = MAKECHUNKID(RwVendor.CRITERIONRM, 0x10)
    sf_CloseConnection          = MAKECHUNKID(RwVendor.CRITERIONRM, 0x11)
    sf_SendTestEvent            = MAKECHUNKID(RwVendor.CRITERIONRM, 0x12)
    sf_Reserved3                = MAKECHUNKID(RwVendor.CRITERIONRM, 0x13)
    sf_Reserved3b               = MAKECHUNKID(RwVendor.CRITERIONRM, 0x14)
    sf_LoadAsset                = MAKECHUNKID(RwVendor.CRITERIONRM, 0x15)
    sf_LoadEmbeddedAsset        = MAKECHUNKID(RwVendor.CRITERIONRM, 0x16)
    sf_Reserved4                = MAKECHUNKID(RwVendor.CRITERIONRM, 0x17)
    sf_GetEntityMatrix          = MAKECHUNKID(RwVendor.CRITERIONRM, 0x18)
    sf_CustomData               = MAKECHUNKID(RwVendor.CRITERIONRM, 0x19)
    sf_FunctionProfiler         = MAKECHUNKID(RwVendor.CRITERIONRM, 0x1A)
    sf_ResetEntity              = MAKECHUNKID(RwVendor.CRITERIONRM, 0x1B)
    sf_PlacementNew             = MAKECHUNKID(RwVendor.CRITERIONRM, 0x1C)
    sf_Initialize               = MAKECHUNKID(RwVendor.CRITERIONRM, 0x1D)
    sf_UpdateAsset              = MAKECHUNKID(RwVendor.CRITERIONRM, 0x1E)
    sf_DynamicSequence          = MAKECHUNKID(RwVendor.CRITERIONRM, 0x1F)
# fmt: on


DEFAULT_VERSION_STAMP = 0x1C020016
