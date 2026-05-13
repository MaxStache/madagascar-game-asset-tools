#pragma array_limit 262144000000000
#pragma pattern_limit 262144000000000

import std.io;
import type.byte;

struct ChunkHeader {
    u32 id;
    u32     payload_size;
    u32     version;
};

struct Vector3 {
    float x;
    float y;
    float z;
};

struct RWColor32 {
    u8 r;
    u8 g;
    u8 b;
    u8 a;
};

struct Texture {
    ChunkHeader header;
    ChunkHeader struct_header;
    
    u8 filterMode;
    u8 addressModes;
    u16 useMipLevels;
    
    ChunkHeader diffuse_header;
    char diffuseTextureName[diffuse_header.payload_size];
    
    ChunkHeader alpha_header;
    char alphaTextureName[alpha_header.payload_size];
   
    ChunkHeader ext_header;
    u8 ext_data[ext_header.payload_size]; 
};

struct Material {
    ChunkHeader header;
    ChunkHeader struct_header;
    
    u32 flags;
    RWColor32 color;
    u32 _unk1;
    u32 isTextured;
    u32 ambient;
    u32 specular;
    u32 diffuse;
    
    if (isTextured != 0) {
        Texture texture;
    }
    
    ChunkHeader ext_header;
    u8 ext_data[ext_header.payload_size]; 
};

struct MaterialList {
    ChunkHeader header; 
    ChunkHeader struct_header;
    
    u32 material_count;
    u32 materialIndices[material_count];
    Material materials[material_count];
};


struct WorldStructData_A {
    u32 numTriangles;
    u32 numVertices;
    u32 numPlaneSectors;
    u32 numAtomicSectors;
    u32 colSectorSize;
    u32 worldFlags;
    
    Vector3 boxMax;
    Vector3 boxMin;
};
struct WorldStructData_B {
    Vector3 boxMax;
    
    u32 numTriangles;
    u32 numVertices;
    u32 numPlaneSectors;
    u32 numAtomicSectors;
    u32 colSectorSize;
    u32 worldFlags;
};

struct UV {
    float u;
    float v;
};

struct Triangle {
    u16 vertex1;
    u16 vertex2;
    u16 vertex3;
    u16 materialIndex;
};

struct AtomicSector {
    // ID already read by parent
    u32 hdr_payload_size;
    u32 hdr_version;
    
    ChunkHeader struct_header;
    
    u32 matListWindowBase;
    u32 num_triangles;
    u32 num_vertices;
    
    Vector3 boxMax;
    Vector3 boxMin;
    
    u32 collSectorPresent;
    u32 _unk1;
    
    Vector3 vertices[num_vertices];
    
    // if not collision
    RWColor32 colors[num_vertices];
    UV uvs[num_vertices];
    // endif
    
    Triangle triangles[num_triangles];
    
    
    // EXT
    ChunkHeader ext_header;
    u8 ext_data[ext_header.payload_size];
}; 

struct PlaneSector {
    // ID already read by parent
    u32 hdr_payload_size;
    u32 hdr_version;
    
    ChunkHeader struct_header;
    
    u32 type;
    float value;
    
    u32 left_is_atomic;
    u32 right_is_atomic;
    
    float left_value;
    float right_value;
    
    // Left Child
    if (left_is_atomic == 1) {
        AtomicSector left_data;
    } else {
        PlaneSector left_data;
    }
    
    // Right Child
    if (right_is_atomic == 1) {
        AtomicSector right_data;
    } else {
        PlaneSector right_data;
    }
}; 

struct WorldChunk {
    u32 section_id;
    
    if (parent.data.numAtomicSectors == 1 && parent.data.numPlaneSectors == 0) {
        AtomicSector data;
    } else if (parent.data.numPlaneSectors > 0) {
        PlaneSector data;
    }
};

struct WorldStruct {
    ChunkHeader header;
    u32 rootIsWorldSector;
    Vector3 inverseOrigin;
    
    if (header.payload_size == 0x40) {
        WorldStructData_A data;
    } else if (header.payload_size == 0x34) {
        WorldStructData_B data;
    } else {
        std::assert(false, "Unknown worldStructSize");
    }
    
    MaterialList matlist;
    
    WorldChunk worldChunk;
    
    
};

struct RWWorld {
    ChunkHeader header;
    WorldStruct wrld_struct;
};

RWWorld my_pattern @ 0x00;