import rwwBSP as rwwBSP
from rwConstants import RWSectionType

vertices = [
    # Bottom
    (4139, -42, 6300),  # 0
    (4139, -42, 6775),  # 1
    (3616, -42, 6775),  # 2
    (3616, -42, 6300),  # 3
    # Top
    (4139, -22, 6300),  # 4
    (4139, -22, 6775),  # 5
    (3616, -22, 6775),  # 6
    (3616, -22, 6300),  # 7
]

triangles = [
    # Bottom
    (0, 1, 2, 0),
    (0, 2, 3, 0),
    # Top
    (4, 6, 5, 0),
    (4, 7, 6, 0),
    # Side 1
    (0, 5, 1, 0),
    (0, 4, 5, 0),
    # Side 2
    (1, 6, 2, 0),
    (1, 5, 6, 0),
    # Side 3
    (2, 7, 3, 0),
    (2, 6, 7, 0),
    # Side 4
    (3, 4, 0, 0),
    (3, 7, 4, 0),
]

bsp = rwwBSP.RW_World()
bspStruct = rwwBSP.RW_WorldStruct()

bspStruct.inverseOrigin = rwwBSP.Vector3(0, 0, 0)
bspStruct.rootIsWorldSector = 0
structData = rwwBSP.WorldStructData_A()
bspStruct.data = structData

structData.numTriangles = len(triangles)
structData.numVertices = len(vertices)
structData.numPlaneSectors = 0
structData.numAtomicSectors = 1

structData.boxMax = rwwBSP.Vector3(4139, -22, 6775)
structData.boxMin = rwwBSP.Vector3(3616, -42, 6300)

bsp.world_struct = bspStruct


matlist = rwwBSP.RW_MaterialList()
matlist.material_count = 1
matlist.materialIndices = [-1]
matlist.materials = [rwwBSP.RW_Material()]
matlist.materials[0].flags = 0
matlist.materials[0].color = rwwBSP.RWColor32(255, 255, 255, 255)
matlist.materials[0].unused = 367978292
matlist.materials[0].isTextured = 0

matlist.materials[0].ambient = 1
matlist.materials[0].specular = 0
matlist.materials[0].diffuse = 1

mat_ext = (
    b"\xf6\x00\x00\x80\x21\x00\x00\x00\x16\x00\x02\x1c\x0d\x00\x0f\x0f"
    b"\x01\x02\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x08\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)
matlist.materials[0].extData = mat_ext

bsp.material_list = matlist


root = rwwBSP.RW_World_RootChunk()
root.section_id = RWSectionType.rwID_ATOMICSECT.value

root_dat = rwwBSP.RW_World_AtomicSector()

root_dat.matListWindowBase = 0
root_dat.numTriangles = len(triangles)
root_dat.numVertices = len(vertices)

boxMax = rwwBSP.Vector3(4139, -22, 6775)
boxMin = rwwBSP.Vector3(3616, -42, 6300)
root_dat.boxMax = boxMax
root_dat.boxMin = boxMin

root_dat.collSectorPresent = 0
root_dat.unused = 0

root_dat.vertices = [rwwBSP.Vector3(vert[0], vert[1], vert[2]) for vert in vertices]
root_dat.colors = [rwwBSP.RWColor32(1, 1, 1, 1) for vert in vertices]

root_dat.uvs = [rwwBSP.RW_UV(0, 0) for vert in vertices]

root_dat.triangles = [rwwBSP.RW_World_Triangle(*tri) for tri in triangles]

root_dat_data = (
    b"\x0e\x05\x00\x00\x0c\x00\x00\x00\x16\x00\x02\x1c\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\xd4\x00\x00\x80\x0c\x00\x00\x00\x16\x00\x02\x1c\x03\x00\x0f\x0f"
    b"\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\xfe\x00\x00\x80\x10\x00\x00\x00\x16\x00\x02\x1c\x03\x00\x0f\x0f"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)

root_dat.extData = root_dat_data


root.data = root_dat

bsp.world_chunk = root


bsp_ext_data = (
    b"\xb0\x00\x00\x80\x10\x00\x00\x00\x16\x00\x02\x1c"
    b"\x03\x00\x0f\x0f\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00"
)

bsp.extData = bsp_ext_data


bsp.save("test.bsp", collision_only_map=False)
bsp.save("test_col.bsp", collision_only_map=True)