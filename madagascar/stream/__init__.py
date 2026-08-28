"""Reading, editing and writing Madagascar .stream level files.

The public surface is unchanged from when this was a single module:

    from madagascar.stream import RW_StreamFile, load_stream
"""

from madagascar.streamfuncs.stringfuncs.sf_CreateEntity import (
    RWSPH_CLASSID,
    RWSPH_CREATECLASSID,
    RWSPH_INSTANCEID,
)

from madagascar.stream.edit import StreamEditMixin
from madagascar.stream.file import RW_StreamFile, load_stream
from madagascar.stream.log import StreamLogMixin
from madagascar.stream.query import StreamQueryMixin

__version__ = "1.0.0"

__all__ = [
    "RW_StreamFile",
    "load_stream",
    "StreamQueryMixin",
    "StreamEditMixin",
    "StreamLogMixin",
    "RWSPH_CLASSID",
    "RWSPH_INSTANCEID",
    "RWSPH_CREATECLASSID",
    "__version__",
]
