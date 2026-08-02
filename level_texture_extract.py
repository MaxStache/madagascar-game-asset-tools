from formats.txd import load_txd

texdict = load_txd("Levels/shuffle/3_TD_LEVEL FOLDER.txd")

texdict.export_all(
    "Levels/shuffle/textures",
)