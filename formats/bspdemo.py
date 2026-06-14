import rwwBSP as rwwBSP

BSP_FILENAME = "19_KingofNY9_Combined188_NoShadow.bsp"
BSP_FILENAME = "15_KingofNY9_Combined188_Opaque.bsp"

bsp = rwwBSP.load_bsp(f"Levels/kingofny/{BSP_FILENAME}")
bsps = [
    rwwBSP.load_bsp("Levels/kingofny/16_KingofNY9_Combined188_Trans.bsp"),
    rwwBSP.load_bsp("Levels/kingofny/18_KingofNY9_Combined188_YonIgnore.bsp"),
    rwwBSP.load_bsp("Levels/kingofny/19_KingofNY9_Combined188_NoShadow.bsp"),
    rwwBSP.load_bsp("Levels/kingofny/15_KingofNY9_Combined188_Opaque.bsp"),
    # rwwBSP.load_bsp("Levels/kingofny/8_KingofNY9_Combined188_Sky.bsp"),
]
rwwBSP.export_bsp_cuts_topdown_png_layers(
    bsps,
    "layered.png",
    resolution=1000,
    geometry_mode="texture",
    txd_paths="Levels/kingofny/2_TD_LEVEL FOLDER.txd",
)
# diffrent_extdata = []
# for mat in bsp.material_list.materials:
#    print("--- EXTENSIONS ---")
#    print(mat.parse_extensions())

""" TFB AtomicSector extension chunk research
atomicSectors = rwwBSP._collect_atomic_sectors(bsp.world_chunk.data)
for i, sector in enumerate(atomicSectors):
    if sector.numVertices == 0:
        continue
    print("----------- SECTOR ----------")
    buf = Parser(sector.extData)
    ext_counter = 0
    while buf.canRead(12): # RWChunkHeader is 12 bytes
        print(f"-- nr. {ext_counter} --")
        chunkHeader = buf.readRWChunkHeader()
        ext_id = chunkHeader.get("id")
        print(ext_id, chunkHeader["size"])
        if ext_id == RWSectionType.rwID_BINMESHPLUGIN.value:
            print("BINMESH")
            buf.skip(chunkHeader["size"])
        elif ext_id == 0x800000D4:
            print("TFB1")
            hex_print = buf.readBytes(chunkHeader["size"]).hex()
            if hex_print != "03000f0f0000000000000000":
                print(hex_print)
        elif ext_id == 0x800000FE:
            print("TFB2")
            hex_print = buf.readBytes(chunkHeader["size"]).hex()
            if hex_print != "03000f0f000000000000000000000000":
                print(hex_print)
        else:
            buf.skip(chunkHeader["size"])
        ext_counter += 1
    #print(len(sector.extData))
"""
