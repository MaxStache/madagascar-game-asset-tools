/*
 * Bin Mesh PLG (Non-Pre-Instanced)
 * RenderWare sector Extension on Geometry
 *
 * Reference:
 * https://gtamods.com/wiki/Bin_Mesh_PLG_(RW_Section)
 *
 * Author: Max Stache
 * Date: 2026-06-15
 */
 
 enum BINMESH_TYPE : u32 {
    TRIANGLE_LIST = 0,
    TRIANGLE_STRIP = 1
 };
 
 struct BINMESH_MESH {
    u32 numIndices; // Indices in this mesh
    u32 materialIndex; // In Geometry´s Material List
    
    u32 indices[numIndices];
 };
 
struct RW_EXT_BINMESHPLG {
    BINMESH_TYPE flags;
    u32 meshCount;
    u32 totalIndices; // Total count of indices
    
    BINMESH_MESH meshes[meshCount];
};

RW_EXT_BINMESHPLG my_binMeshPLG @ 0x00;