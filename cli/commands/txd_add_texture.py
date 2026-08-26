from madagascar.sections.TEXTURENATIVE_0015 import create_texture

from ..cli import app
from ..utils import (
    ValidatedExistingFile,
)
from madagascar.txd import load_txd
from pathlib import Path
from PIL import Image

@app.command
def txd_add_texture(
    txd_file: ValidatedExistingFile,
    texture_file: ValidatedExistingFile,
):
    """Add a texture to a TXD. THIS ONLY WORKS FOR XBOX TEXTURE DICTIONARYS!

    Parameters
    ----------
    txd_file : str
        File to unpack.
    texture_file : str
        BMP file to add
    """

    texture_name = Path(texture_file).stem

    image = Image.open(texture_file).convert("RGBA")

    pixel_data = image.tobytes()

    txdfile = load_txd(txd_file)
    txdfile.add_texture(
        create_texture(
            name=texture_name,
            rgba=pixel_data,
            width=image.size[0],
            height=image.size[1],
        )
    )

    with open(txd_file, "wb") as f:
        txdfile.write(f, txdfile.header.library_id_stamp)