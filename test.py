from pathlib import Path

from madagascar.lpa import load_lpa, RW_TFB_LipAnimation
from madagascar.stream import load_stream


with open("Marty_go.wav", "rb") as f:
    data = f.read()
marty_go_lpa = RW_TFB_LipAnimation.generate_from_wav(data)

print(marty_go_lpa)

#load_stream("Levels/kingofny.stream").write_log("kingofny.gig.txt")
#lpa = load_lpa(
#    Path("Levels/kingofny/1987_Marty_go.lpa")
#)
#print(lpa.visemes)
#print(lpa.duration)