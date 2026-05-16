import rwwBSP as rwwBSP
import rwtxd as rwtxd
import os

txd = rwtxd.load("Levels/banquet/3_TD_LEVEL FOLDER.txd")

DIRECTORY = "BSPTEST/"
TEX_DIRECTORY = f"{DIRECTORY}textures/"
os.makedirs(TEX_DIRECTORY, exist_ok=True)

COLMAP = False

#BSP_FILENAME = "19_JungleBanquet_working_export_NoShadow.bsp"
BSP_FILENAME = "16_JungleBanquet_working_export_Opaque.bsp"
#BSP_FILENAME = "10_JungleBanquet_working_export_Col.bsp"

#for texture in txd.textures:
#    rwtxd.export_png(texture, f"{TEX_DIRECTORY}{texture.name}.png")

bsp = rwwBSP.load_bsp(f"Levels/banquet/{BSP_FILENAME}", collision_only_map=COLMAP)

#rwwBSP.export_obj(
#    bsp,
#    f"{DIRECTORY}/noshadow_export.obj",
#    f"{DIRECTORY}/noshadow_export.mtl",
#    collision_only_map=COLMAP,
#)

rwwBSP.export_gltf(
    bsp,
    f"{DIRECTORY}/noshadow_export.gltf",
    f"{DIRECTORY}/noshadow_export.bin",
    f"{DIRECTORY}/textures/",
    collision_only_map=COLMAP,
)

# bsp.save("test.bsp")

# bsp1 = rwwBSP.load_bsp("test.bsp")
