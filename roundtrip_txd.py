from madagascar.txd import load_txd

mytxd = load_txd("Levels/KingOfNY-unchanged/2_TD_LEVEL FOLDER.txd")

with open("out.txd", "wb") as f:
    mytxd.write(f, mytxd.header.library_id_stamp)



with open("out.txd", "rb") as f:
    a = f.read()
with open("Levels/KingOfNY-unchanged/2_TD_LEVEL FOLDER.txd", "rb") as f:
    b = f.read()

if len(a) != len(b):
    print(f"size mismatch: {len(a)} vs {len(b)}")

diff = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))
print(f"{diff} bytes differ")
print("ROUNDTRIP OKAY" if diff == 0 else "ROUNDTRIP FAILED")