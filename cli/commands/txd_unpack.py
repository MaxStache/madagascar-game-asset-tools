from ..cli import app
from ..utils import (
    ValidatedExistingFile,
    ValidatedDir,
)
from madagascar.txd import load_txd
import os

@app.command
def txd_unpack(
    txd_file: ValidatedExistingFile,
    output_dir: ValidatedDir,
):
    """Unpack all textures of a txd into a folder

    Parameters
    ----------
    txd_file : str
        File to unpack.
    output_dir : str
        Directory to unpack the stream file into.
    """

    os.makedirs(output_dir, exist_ok=True)
    txdfile = load_txd(txd_file)
    txdfile.export_all(output_dir, raise_on_error=True)