import rwwBSP as rwwBSP
#from rwConstants import RWSectionType
#
#vertices = [
#    # Bottom (y=-50)
#    (33716.79, -50, -36008.3),  # 0
#    (33716.79, -50, 57756.996),  # 1
#    (-60048.508, -50, 57756.996),  # 2
#    (-60048.508, -50, -36008.3),  # 3
#    # Top (y=0)
#    (33716.79, 0, -36008.3),  # 4
#    (33716.79, 0, 57756.996),  # 5
#    (-60048.508, 0, 57756.996),  # 6
#    (-60048.508, 0, -36008.3),  # 7
#]
#
#triangles = [
#    # Bottom
#    (0, 1, 2, 0),
#    (0, 2, 3, 0),
#    # Top
#    (4, 6, 5, 0),
#    (4, 7, 6, 0),
#    # Side 1
#    (0, 5, 1, 0),
#    (0, 4, 5, 0),
#    # Side 2
#    (1, 6, 2, 0),
#    (1, 5, 6, 0),
#    # Side 3
#    (2, 7, 3, 0),
#    (2, 6, 7, 0),
#    # Side 4
#    (3, 4, 0, 0),
#    (3, 7, 4, 0),
#]
#
#
#bsp = rwwBSP.RW_World()
#bspStruct = rwwBSP.RW_WorldStruct()
#
#bspStruct.inverseOrigin = rwwBSP.Vector3(-0, -0, -0)
#bspStruct.rootIsWorldSector = 1
#structData = rwwBSP.WorldStructData_A()
#bspStruct.data = structData
#
#structData.numTriangles = len(triangles)
#structData.numVertices = len(vertices)
#structData.numPlaneSectors = 0
#structData.numAtomicSectors = 1
#structData.colSectorSize = 0
#structData.worldFlags = 0x4001004D
#
#structData.boxMax = rwwBSP.Vector3(33716.79, 45612.477, 57756.996)
#structData.boxMin = rwwBSP.Vector3(-60048.508, -48152.82, -36008.3)
#
#bsp.world_struct = bspStruct
#
#
#matlist = rwwBSP.RW_MaterialList()
#matlist.material_count = 1
#matlist.materialIndices = [-1]
#matlist.materials = [rwwBSP.RW_Material()]
#matlist.materials[0].flags = 0
#matlist.materials[0].color = rwwBSP.RWColor32(255, 255, 255, 255)
#matlist.materials[0].unused = 853987164
#matlist.materials[0].isTextured = 1
#
#matlist.materials[0].texture = rwwBSP.RW_Texture()
#matlist.materials[0].texture.filterMode = 2
#matlist.materials[0].texture.addressModes = 51
#matlist.materials[0].texture.useMipLevels = 1
#matlist.materials[0].texture.diffuseTextureName = "REP_ROOF1"
#matlist.materials[0].texture.alphaTextureName = ""
#
#
#matlist.materials[0].ambient = 1
#matlist.materials[0].specular = 0
#matlist.materials[0].diffuse = 1
#
#mat_ext = (
#    b"\xf6\x00\x00\x80\x21\x00\x00\x00\x16\x00\x02\x1c\x0d\x00\x0f\x0f"
#    b"\x01\x02\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x08\x00\x00\x00"
#    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
#)
#matlist.materials[0].extData = mat_ext
#
#bsp.material_list = matlist
#
#
#root = rwwBSP.RW_World_RootChunk()
#root.section_id = RWSectionType.rwID_ATOMICSECT.value
#
#root_dat = rwwBSP.RW_World_AtomicSector()
#
#root_dat.matListWindowBase = 0
#root_dat.numTriangles = len(triangles)
#root_dat.numVertices = len(vertices)
#
#boxMin = rwwBSP.Vector3(-60048.508, -50, -36008.3)
#boxMax = rwwBSP.Vector3(33716.79, 0, 57756.996)
#root_dat.boxMax = boxMax
#root_dat.boxMin = boxMin
#
#root_dat.collSectorPresent = 1232928
#root_dat.unused = 0
#
#root_dat.vertices = [rwwBSP.Vector3(vert[0], vert[1], vert[2]) for vert in vertices]
#root_dat.colors = [rwwBSP.RWColor32(255, 255, 255, 255) for vert in vertices]
#
#root_dat.uvs = [rwwBSP.RW_UV(0, 0) for vert in vertices]
#
#root_dat.triangles = [rwwBSP.RW_World_Triangle(*tri) for tri in triangles]
#
#root_dat_data = (
#    b"\x0e\x05\x00\x00\x0c\x00\x00\x00\x16\x00\x02\x1c\x00\x00\x00\x00"
#    b"\x00\x00\x00\x00\x00\x00\x00\x00"
#    b"\xd4\x00\x00\x80\x0c\x00\x00\x00\x16\x00\x02\x1c\x03\x00\x0f\x0f"
#    b"\x00\x00\x00\x00\x00\x00\x00\x00"
#    b"\xfe\x00\x00\x80\x10\x00\x00\x00\x16\x00\x02\x1c\x03\x00\x0f\x0f"
#    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
#)
#
#root_dat.extData = root_dat_data
#
#
#root.data = root_dat
#
#bsp.world_chunk = root
#
#
#bsp_ext_data = (
#    b"\xb0\x00\x00\x80\x10\x00\x00\x00\x16\x00\x02\x1c"
#    b"\x03\x00\x0f\x0f\x00\x00\x00\x00\x00\x00\x00\x00"
#    b"\x00\x00\x00\x00"
#)
#
#bsp.extData = bsp_ext_data


#bsp.save(
#    "Levels/KingOfNY/13_KingofNY9_Combined188_NoShadow.bsp", collision_only_map=False
#)
# bsp.save("Levels/KingOfNY/9_KingofNY9_Combined188_Opaque.bsp", collision_only_map=False)
# bsp.save("Levels/KingOfNY/10_KingofNY9_Combined188_Trans.bsp", collision_only_map=False)
# bsp.save("Levels/KingOfNY/12_KingofNY9_Combined188_YonIgnore.bsp", collision_only_map=False)
# bsp.save("Levels/KingOfNY/6_KingofNY9_Combined188_Col.bsp", collision_only_map=True)


orig = rwwBSP.load_bsp(
    "Levels/KingOfNY-unchanged/13_KingofNY9_Combined188_NoShadow.bsp"
)

for sector in rwwBSP._collect_atomic_sectors(orig.world_chunk.data):
    #vs = sector.vertices
    #sector.vertices = [
    #    rwwBSP.Vector3(vs[v].x, vs[v-1].y, vs[v].z) for v in range(len(sector.vertices))
    #]
    sector.triangles = [rwwBSP.RW_World_Triangle(t.vertex1, t.vertex2, t.vertex3, t.materialIndex + 1) for t in sector.triangles]
    # sector.boxMax = rwwBSP.Vector3(sector.boxMax.x, sector.boxMax.y + 40, sector.boxMax.z)
    # sector.boxMin = rwwBSP.Vector3(sector.boxMin.x, sector.boxMin.y + 40, sector.boxMin.z)

    if sector.numVertices != 0:
        print(sector.ext_header.pack())
        print()
        print()
        print()
        print(sector.extData)
        print()
        exit()

orig.save(
    "Levels/KingOfNY/13_KingofNY9_Combined188_NoShadow.bsp", collision_only_map=False
)
