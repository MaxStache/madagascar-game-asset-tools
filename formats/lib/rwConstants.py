from enum import Enum, IntEnum


class RWSectionType_TFB(Enum):
    rwID_tfbMATFXEFFECTUVTRANSFORM = 0x800000F6


def MAKECHUNKID(vId, sId):
    """
    vId = vendorID
    sId = section identifier
    """
    return ((vId & 0xFFFFFF) << 8) | (sId & 0xFF)

class RwVendor(IntEnum):
    # --- RW / Criterion ---
    CORE = 0x000000  # Core engine
    CRITERIONTK = 0x000001  # Toolkit utilities (Rt* libraries).
    REDLINERACER = 0x000002 # Internal Redline Racer module.
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
    rwID_NAOBJECT              = 0x0000
    rwID_STRUCT                = 0x0001
    rwID_STRING                = 0x0002
    rwID_EXTENSION             = 0x0003
    rwID_CAMERA                = 0x0005
    rwID_TEXTURE               = 0x0006
    rwID_MATERIAL              = 0x0007
    rwID_MATLIST               = 0x0008
    rwID_ATOMICSECT            = 0x0009
    rwID_PLANESECT             = 0x000A
    rwID_WORLD                 = 0x000B
    rwID_SPLINE                = 0x000C
    rwID_MATRIX                = 0x000D
    rwID_FRAMELIST             = 0x000E
    rwID_GEOMETRY              = 0x000F
    rwID_CLUMP                 = 0x0010
    rwID_LIGHT                 = 0x0012
    rwID_UNICODESTRING         = 0x0013
    rwID_ATOMIC                = 0x0014
    rwID_TEXTURENATIVE         = 0x0015                                        # also known as Raster
    rwID_TEXDICTIONARY         = 0x0016
    rwID_ANIMDATABASE          = 0x0017
    rwID_IMAGE                 = 0x0018
    rwID_SKINANIMATION         = 0x0019
    rwID_GEOMETRYLIST          = 0x001A
    rwID_ANIMANIMATION         = 0x001B
    rwID_TEAM                  = 0x001C
    rwID_CROWD                 = 0x001D
    rwID_DMORPHANIMATION       = 0x001E
    rwID_RIGHTTORENDER         = 0x001F
    rwID_MTEFFECTNATIVE        = 0x0020
    rwID_MTEFFECTDICT          = 0x0021
    rwID_TEAMDICTIONARY        = 0x0022
    rwID_PITEXDICTIONARY       = 0x0023
    rwID_TOC                   = 0x0024
    rwID_PRTSTDGLOBALDATA      = 0x0025
    rwID_ALTPIPE               = 0x0026
    rwID_PIPEDS                = 0x0027
    rwID_PATCHMESH             = 0x0028
    rwID_CHUNKGROUPSTART       = 0x0029
    rwID_CHUNKGROUPEND         = 0x002A
    rwID_UVANIMDICT            = 0x002B
    rwID_COLLTREE              = 0x002C
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
    rwaID_OBJDEFALIAS      = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x00)
    rwaID_OBJDEFALIAS_DATA = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x01)
       # single wave
    rwaID_WAVE       = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x02)
    rwaID_WAVESTRUCT = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x03)
    rwaID_WAVEDATA   = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x04)
       # object dictionary
    rwaID_OBJDICT                = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x05)
    rwaID_OBJDICTOBJDEFALIAS     = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x06)
    rwaID_OBJDICTOBJDEFALIAS_HDR = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x07)
    rwaID_OBJDICTOBJDEFALIAS_DAT = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x08)
       # wave dictionary
    rwaID_WAVEDICT              = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x09)
    rwaID_WAVEDICT_DICT         = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0A)
    rwaID_WAVEDICT_WAVE_HDR     = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0B)
    rwaID_WAVEDICT_WAVE         = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0C)
    rwaID_WAVEDICT_WAVEDATA_HDR = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0D)
    rwaID_WAVEDICT_WAVEDATA     = MAKECHUNKID(RwVendor.CRITERIONRWA, 0x0E)

    # TFB
    rwID_tfb_AtomicSec1    = MAKECHUNKID(RwVendor.TFB, 0xD4)  # found on atomic world sector - 12B
    rwID_tfb_AtomicSec2    = MAKECHUNKID(RwVendor.TFB, 0xFE)  # found on atomic world sector - 16B
    rwID_tfb_World1        = MAKECHUNKID(RwVendor.TFB, 0xB0)  # found on world - 16B
    rwID_tfb_Material1     = MAKECHUNKID(RwVendor.TFB, 0xF6)  # found on material (in world) - 33B
    rwID_tfb_Atomic1       = MAKECHUNKID(RwVendor.TFB, 0xED)  # found on atomic - 12B
    rwID_tfb_Atomic2       = MAKECHUNKID(RwVendor.TFB, 0xFD)  # found on atomic - 28B
    rwID_tfb_Clump1        = MAKECHUNKID(RwVendor.TFB, 0xB1)  # found on clump - 8B
    rwID_tfb_TextureNative = MAKECHUNKID(RwVendor.TFB, 0xDD)  # found on TextureNative - 12B

# fmt: on


class strfunc_func(Enum):
    sf_VersionNumber = -1

    sf_Reset = 0

    sf_Reserved1 = 1
    sf_Reserved2 = 2

    sf_SetDirectorsCameraMatrix = 3

    sf_CreateEntity = 4
    sf_UpdateEntityAttributes = 5

    sf_SetFrozenMode = 6
    sf_SetRunningMode = 7

    sf_EnableDirectorsCamera = 8
    sf_DisableDirectorsCamera = 9

    sf_TextComment = 10

    sf_StartSystem = 11
    sf_StopSystem = 12

    sf_DeleteEntity = 13
    sf_DeleteAllEntities = 14

    sf_UnLoadAsset = 15

    sf_Shutdown = 16
    sf_CloseConnection = 17
    sf_SendTestEvent = 18

    sf_Reserved3 = 19
    sf_Reserved3b = 20

    sf_LoadAsset = 21

    sf_LoadEmbeddedAsset = 22

    sf_Reserved4 = 23

    sf_GetEntityMatrix = 24

    sf_CustomData = 25

    sf_FunctionProfiler = 26

    sf_ResetEntity = 27

    sf_PlacementNew = 28

    sf_Initialize = 29

    sf_UpdateAsset = 30

    sf_DynamicSequence = 31


DEFAULT_VERSION_STAMP = 0x1C020016
