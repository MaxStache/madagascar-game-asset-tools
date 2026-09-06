from madagascar.stream import load_stream

level = load_stream("levels/kingofny.stream") # replace kingofny.stream with the level you wanna mod

# level.write_log("kingofny.gig.txt") # You can enable this to show the stream in a human readable form

# =================================

# YOUR MODDING CODE HERE ;)

# =================================

level.updatePlacementNew()

# replace this with the path where the .stream should be saved 

# == TIP ==
# You can also replace this with the correct path to the correct .stream file in your game folder,
# after that you can just start the game and load the level and your changes will be there!
# ========

level.save("modified_kingofny.stream")
