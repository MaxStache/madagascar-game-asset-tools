from tfbscript import ScriptFile, open_editor

scr = ScriptFile.from_path(r"C:\Users\maxst\Projects\madagascar-tfbscript\example_scripts\rave\150_GameMaster_Interface.ai")
open_editor(scr)

#from madagascar.stream import load_stream
#
#load_stream("./Levels/rave.stream").write_log("ravelog.gig.txt")