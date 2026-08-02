from formats.txd import load_txd

ALL_MIPMAPS = False

mytxd = load_txd("test/2_TD_LEVEL FOLDER.txd")

mytxd.export_all("TEST_TXD_EXPORT", all_mipmaps=ALL_MIPMAPS)

mytxd = load_txd("Levels/Beach/3_TD_LEVEL FOLDER.txd")

mytxd.export_all("BEACH_TXD_EXPORT", all_mipmaps=ALL_MIPMAPS)


mytxd = load_txd("Levels/KingOfNY/2_TD_LEVEL FOLDER.txd")

mytxd.export_all("Levels/KingOfNY/textures", all_mipmaps=ALL_MIPMAPS)