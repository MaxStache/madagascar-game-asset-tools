from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from formats.bsp import load_bsp

mybsp = load_bsp("Levels/KingOfNY-unchanged/10_KingofNY9_Combined188_Trans.bsp")