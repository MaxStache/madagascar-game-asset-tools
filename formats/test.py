from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from formats.lib.rwConstants import DEFAULT_VERSION_STAMP

from formats.stream import load_stream

strm = load_stream("kingofny.stream")
#load_stream("banquet.stream")

with open("kingofny_out.stream", "wb") as f:
    strm.write(f, DEFAULT_VERSION_STAMP)