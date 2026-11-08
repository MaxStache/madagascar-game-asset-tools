"""Reading, editing and writing Madagascar .stream level files.

The public surface is unchanged from when this was a single module:

    from madformats.stream import RW_StreamFile, load_stream
"""

from madformats.stream.edit import StreamEditMixin
from madformats.stream.file import RW_StreamFile, load_stream
from madformats.stream.log import StreamLogMixin
from madformats.stream.query import StreamQueryMixin
from madformats.streamfuncs.stringfuncs.sf_CreateEntity import (
    RWSPH_CLASSID,
    RWSPH_CREATECLASSID,
    RWSPH_INSTANCEID,
)

__version__ = "1.0.0"

__all__ = [
    "RWSPH_CLASSID",
    "RWSPH_CREATECLASSID",
    "RWSPH_INSTANCEID",
    "RW_StreamFile",
    "StreamEditMixin",
    "StreamLogMixin",
    "StreamQueryMixin",
    "__version__",
    "load_stream",
]
