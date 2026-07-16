import io

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from formats.stream import load_stream

load_stream("kingofny.stream")
#load_stream("banquet.stream")