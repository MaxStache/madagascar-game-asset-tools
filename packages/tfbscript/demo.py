# from tfbscript import ScriptFile
# from tfbscript import open_editor, editor_from_filepath
from tfbscript import editor_from_filepath
# from contextlib import redirect_stdout

# script = ScriptFile.from_path(
#    #"PR_Pause_{0974a777-cf50-4185-857d-810db4807d9a}.ai.mod",
#    r"C:\Users\maxst\Projects\madagascar-game-asset-tools\Levels\german\golf\golfball_as_player_{802e7002-2517-40a2-9658-5a17f51ad463}.ai",
#    debugOptions={
#        "listUnresolvedOps": True,
#    },
# )
#
# with open("log.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
#    script.print_tree()
#
# open_editor(script)

PATH = r"C:\Users\maxst\Projects\madagascar-tfbscript\example_scripts\lemurs\670_SL_LemurConvoy.ai"

editor_from_filepath(PATH)

# with open("PR_Pause_{0974a777-cf50-4185-857d-810db4807d9a}.ai.mod", "wb") as f:
#   script.write(f)
