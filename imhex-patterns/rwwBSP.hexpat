// rwwBSP.hexpat — RenderWare World BSP ImHex Pattern
// Matches the binary layout described in rwwBSP.py

#pragma endian little
#pragma pattern_limit 4000000
#pragma array_limit 1000000

// ═══════════════════════════════════════════════════════
// Enums
// ═══════════════════════════════════════════════════════

enum RWSectionType : u32 {
    rwID_NAOBJECT                  = 0x0000,
    rwID_STRUCT                    = 0x0001,
    rwID_STRING                    = 0x0002,
    rwID_EXTENSION                 = 0x0003,
    rwID_CAMERA                    = 0x0005,
    rwID_TEXTURE                   = 0x0006,
    rwID_MATERIAL                  = 0x0007,
    rwID_MATLIST                   = 0x0008,
    rwID_ATOMICSECT                = 0x0009,
    rwID_PLANESECT                 = 0x000A,
    rwID_WORLD                     = 0x000B,
    rwID_SPLINE                    = 0x000C,
    rwID_MATRIX                    = 0x000D,
    rwID_FRAMELIST                 = 0x000E,
    rwID_GEOMETRY                  = 0x000F,
    rwID_CLUMP                     = 0x0010,
    rwID_LIGHT                     = 0x0012,
    rwID_UNICODESTRING             = 0x0013,
    rwID_ATOMIC                    = 0x0014,
    rwID_TEXTURENATIVE             = 0x0015,
    rwID_TEXDICTIONARY             = 0x0016,
    rwID_GEOMETRYLIST              = 0x001A,
    rwID_UVANIMDICT                = 0x002B,
    rwID_COLLTREE                  = 0x002C,
    rwID_HANIMPLUGIN               = 0x011E,
    rwID_USERDATAPLUGIN            = 0x011F,
    rwID_MATERIALEFFECTSPLUGIN     = 0x0120,
    rwID_BINMESHPLUGIN             = 0x050E,
    rwID_NATIVEDATAPLUGIN          = 0x0510,
    rwID_ZModelerLock              = 0x0000F21E,
    rwID_Frame                     = 0x0253F2FE,
    rwID_TFB_MATFXEFFECTUVTRANSFORM = 0x800000F6,
};

enum PlaneSectorType : u32 {
    rwPLANE_X = 0,  // byte offset of x in RwV3d
    rwPLANE_Y = 4,  // byte offset of y in RwV3d
    rwPLANE_Z = 8,  // byte offset of z in RwV3d
};

// ═══════════════════════════════════════════════════════
// Primitive Types
// ═══════════════════════════════════════════════════════

struct RWHeader {
    RWSectionType type;
    u32 size;
    u32 library_id_stamp;
} [[static]];

struct Vector3 {
    float x, y, z;
} [[static]];

struct RWColor32 {
    u8 r, g, b, a;
} [[static, color(str::format("{:02X}{:02X}{:02X}", r, g, b))]];

struct RW_UV {
    float u, v;
} [[static]];

struct RW_World_Triangle {
    u16 vertex1, vertex2, vertex3;
    u16 materialIndex;
} [[static]];

// ═══════════════════════════════════════════════════════
// Texture Chunk (rwID_TEXTURE = 0x0006)
// ═══════════════════════════════════════════════════════

struct RW_Texture {
    RWHeader header;              // rwID_TEXTURE

    RWHeader struct_header;       // rwID_STRUCT, size = 4
    u8  filterMode;
    u8  addressModes;
    u16 useMipLevels;

    RWHeader diffuse_hdr;         // rwID_STRING
    char diffuseTextureName[diffuse_hdr.size];

    RWHeader alpha_hdr;           // rwID_STRING
    char alphaTextureName[alpha_hdr.size];

    RWHeader ext_header;          // rwID_EXTENSION
    u8 extData[ext_header.size];
};

// ═══════════════════════════════════════════════════════
// Material Chunk (rwID_MATERIAL = 0x0007)
// ═══════════════════════════════════════════════════════

struct RW_Material {
    RWHeader header;              // rwID_MATERIAL

    RWHeader struct_header;       // rwID_STRUCT, size = 28
    u32       flags;              // always 0 in tested files
    RWColor32 color;
    u32       unused;             // always 367978292 (0x15F2DAAF) in tested files
    u32       isTextured;

    float ambient;
    float specular;
    float diffuse;

    if (isTextured != 0) {
        RW_Texture texture;
    }

    RWHeader ext_header;          // rwID_EXTENSION
    u8 extData[ext_header.size];
};

// ═══════════════════════════════════════════════════════
// Material List Chunk (rwID_MATLIST = 0x0008)
// ═══════════════════════════════════════════════════════

struct RW_MaterialList {
    RWHeader header;              // rwID_MATLIST

    RWHeader struct_header;       // rwID_STRUCT
    u32 material_count;
    // -1 = this slot is a material definition
    // >= 0 = index of base material this is an instance of
    s32 materialIndices[material_count];

    RW_Material materials[material_count];
};

// ═══════════════════════════════════════════════════════
// World Struct payload variants
//   size == 0x40 → Type A  (boxMin present, counts first)
//   size == 0x30 → Type B  (boxMax first, no boxMin)
// ═══════════════════════════════════════════════════════

struct WorldStructData_A {
    u32     numTriangles;
    u32     numVertices;
    u32     numPlaneSectors;
    u32     numAtomicSectors;
    u32     colSectorSize;
    u32     worldFlags;
    Vector3 boxMax;
    Vector3 boxMin;
};

struct WorldStructData_B {
    Vector3 boxMax;
    u32     numTriangles;
    u32     numVertices;
    u32     numPlaneSectors;
    u32     numAtomicSectors;
    u32     colSectorSize;
    u32     worldFlags;
};

struct RW_WorldStruct {
    RWHeader header;              // rwID_STRUCT, size = 0x40 or 0x30
    u32     rootIsWorldSector;    // usually 0
    Vector3 inverseOrigin;        // usually -0 -0 -0

    if (header.size == 0x40) {
        WorldStructData_A data;
    } else {
        WorldStructData_B data;
    }
};

// ═══════════════════════════════════════════════════════
// Atomic Sector  — BSP leaf node (rwID_ATOMICSECT = 0x0009)
//
// NOTE: For collision-only BSPs (TFB games), UVs are absent.
//       Remove the `uvs` array below for those files.
// ═══════════════════════════════════════════════════════

struct RW_World_AtomicSector {
    u32 hdr_payload_size;         // total payload size (excl. these 2 u32s)
    u32 hdr_version;

    RWHeader struct_header;       // rwID_STRUCT

    u32     matListWindowBase;    // offset into global material list
    u32     numTriangles;
    u32     numVertices;
    Vector3 boxMax;
    Vector3 boxMin;
    u32     collSectorPresent;
    u32     unused;               // always 0 in tested files

    Vector3        vertices[numVertices];
    RWColor32      colors[numVertices];
    RW_UV          uvs[numVertices];      // absent for collision-only BSPs
    RW_World_Triangle triangles[numTriangles];

    RWHeader ext_header;          // rwID_EXTENSION
    u8 extData[ext_header.size];
};

// ═══════════════════════════════════════════════════════
// Plane Sector — BSP internal node (rwID_PLANESECT = 0x000A)
//
// The tree is recursive: each child is either another
// PlaneSector or an AtomicSector, determined by left/right_is_atomic.
//
// Each child is preceded by its section_id u32 (0x0009 or 0x000A).
// ═══════════════════════════════════════════════════════

struct RW_World_PlaneSector {
    u32 hdr_payload_size;
    u32 hdr_version;

    RWHeader struct_header;       // rwID_STRUCT, size = 24

    PlaneSectorType type;         // split axis: 0=X  4=Y  8=Z
    float value;                  // position of the split plane along that axis
    u32   left_is_atomic;         // 1 = left child is AtomicSector
    u32   right_is_atomic;        // 1 = right child is AtomicSector
    float left_value;             // actual extent of the left  sub-box (may overlap)
    float right_value;            // actual extent of the right sub-box (may overlap)

    // Left child
    u32 left_child_id;            // rwID_ATOMICSECT=0x0009  or  rwID_PLANESECT=0x000A
    if (left_is_atomic != 0) {
        RW_World_AtomicSector left_data;
    } else {
        RW_World_PlaneSector  left_data;
    }

    // Right child
    u32 right_child_id;
    if (right_is_atomic != 0) {
        RW_World_AtomicSector right_data;
    } else {
        RW_World_PlaneSector  right_data;
    }
};

// ═══════════════════════════════════════════════════════
// Root Chunk — first sector after the material list.
// The section_id tells us which sector type follows.
// ═══════════════════════════════════════════════════════

struct RW_World_RootChunk {
    u32 section_id;               // rwID_ATOMICSECT or rwID_PLANESECT
    if (section_id == 0x0009) {
        RW_World_AtomicSector data;
    } else if (section_id == 0x000A) {
        RW_World_PlaneSector  data;
    }
};

// ═══════════════════════════════════════════════════════
// Top-level World  (rwID_WORLD = 0x000B)
// ═══════════════════════════════════════════════════════

struct RW_World {
    RWHeader header;              // rwID_WORLD = 0x000B
    RW_WorldStruct   world_struct;
    RW_MaterialList  material_list;
    RW_World_RootChunk world_chunk;
    RWHeader ext_header;          // rwID_EXTENSION = 0x0003
    u8 extData[ext_header.size];
};

// ═══════════════════════════════════════════════════════
// Entry point
// ═══════════════════════════════════════════════════════

RW_World world @ 0x00;
