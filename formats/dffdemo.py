from rwConstants import RWSectionType
from rwDFF import load_dff
from rwwBSP import load_bsp, _collect_atomic_sectors

from pathlib import Path
from sections import RW_Extension
from lib.parser import Parser

trans = load_bsp("Levels/KingOfNY-unchanged/10_KingofNY9_Combined188_Trans.bsp")
ext = trans.material_list.materials[5].extension
 
print(ext.children[0])

with open("test_ext.bin", "rb") as f:
    ext = RW_Extension.read(Parser(f.read()), RWSectionType.rwID_ATOMICSECT.value)

    


all_dffs = list(Path("Levels/KingOfNY-unchanged/").glob("*.dff"))

for dff_path in all_dffs:
    try:
        mydff = load_dff(dff_path)
    except Exception as e:
        print(f"Failed to load {dff_path}: {e}")
