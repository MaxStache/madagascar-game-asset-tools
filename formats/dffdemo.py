# from rwConstants import RWSectionType
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from formats.txd import load_txd
from formats.sections.TEXTURENATIVE_0015 import RW_TextureNative

dict = load_txd("Levels/banquet/3_TD_LEVEL FOLDER.txd")

#dict.textures[0].export_png("test.png")
#
#tex = RW_TextureNative.from_png("test.png", name="test")
#
#dict.add_texture(tex)
#
#orange = dict.find_texture_by_name("orange")
#
#dict.write("2_TD_LEVEL FOLDER.txd", stamp=0x3600, parent=None)
#

dict.export_all("Levels/banquet/textures")