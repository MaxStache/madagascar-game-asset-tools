from pathlib import Path

from ..cli import app
from ..utils import (
    ValidatedExistingDir,
)
from .unpack import unpack, FileNaming
import os

@app.command
def unpack_directory(
    stream_folder_dir: ValidatedExistingDir,
    naming: FileNaming = FileNaming.SEC_IDX,
    human: bool = True,
    gzipped: bool = False,
):
    """Unpack all stream files in a directory, for more info look at the command "unpack".

    Parameters
    ----------
    stream_folder_dir : str
        Folder with the .stream files in it
    human : bool
        Whether to make the manifest more human-readable (pretty-printed).
    gzipped : bool
        Whether the stream file is gzipped or not.
    """
    for file in Path(stream_folder_dir).glob("*.stream"):
        output_dir = Path(stream_folder_dir, file.stem)
        os.makedirs(output_dir, exist_ok=True)
        unpack(file, output_dir, naming=naming, human=human, gzipped=gzipped)