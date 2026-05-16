
import rwtxd as rwtxd

txd = rwtxd.load("Levels/golf/2_TD_LEVEL FOLDER.txd")
for texture in txd.textures:
    rwtxd.export_png(texture, f"Levels/golf/textures/{texture.name}.png")
