from pathlib import Path

from madagascar.stream import load_stream

MOD_DIRECTORY = Path("mods/kingofny/goldCoins10/")

level = load_stream(
    "levels/kingofny.stream"
)  # replace kingofny.stream with the level you wanna mod

level.write_log(
    "kingofny.gig.txt"
)  # You can enable this to show the stream in a human readable form

level.assetByName("DG_Coin_Collectable.AI").importFrom(Path(MOD_DIRECTORY, "data/scripts/DG_Coin_Collectable.AI"))




level.updatePlacementNew()

level.verify()

level.save("../../Desktop/Madagascar/Game/Levels/kingofny.stream")
