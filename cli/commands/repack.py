from ..cli import app
from ..utils import ValidatedDir, ValidatedFile, progress
from madagascar.lib.rwConstants import strfunc_func
import json
import io
from pathlib import Path
from typing import cast
from madagascar.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import RW_sf_LoadEmbeddedAsset
from madagascar.stream import RW_StreamFile
from madagascar.streamfuncs import STRFUNC_REGISTRY
from madagascar.lib.rw_basics import RW_StreamFunc_NotImplemented

@app.command
def repack(
    input_dir: ValidatedDir, out_stream_file_dir: ValidatedFile, gzipped: bool = False
):
    """Repack a stream from a directory (including a manifest).

    Parameters
    ----------
    input_dir : str
        Directory to repack from.
    out_stream_file_dir : str
        File to repack into.
    gzipped : bool
        Whether the output stream file should be gzipped or not.
    """

    MANIFEST_FILE = Path(input_dir, "manifest.json")

    with open(MANIFEST_FILE, "r") as f:
        manifest_contents = json.load(f)

    strm = RW_StreamFile()
    for sec_dict in progress(manifest_contents, description="Processing..."):
        streamfunc_name = sec_dict.pop("streamfunc")
        file_name = sec_dict.pop("file_name", None)
        streamfunc = strfunc_func[streamfunc_name] if streamfunc_name else None

        assert streamfunc is not None, (
            f"Streamfunc {streamfunc_name} not found in manifest."
        )

        streamfunc_class = STRFUNC_REGISTRY.get(
            streamfunc.value, RW_StreamFunc_NotImplemented
        )

        streamfunc_inst = streamfunc_class.from_dict(sec_dict)

        if streamfunc == strfunc_func.sf_LoadEmbeddedAsset:
            sec = cast(RW_sf_LoadEmbeddedAsset, streamfunc_inst)
            assert file_name is not None, (
                "Manifest entry is missing 'file_name' for sf_LoadEmbeddedAsset."
            )
            with open(Path(input_dir, file_name), "rb") as f:
                sec.data = f.read()
        strm.contents.append(streamfunc_inst)

    buf = io.BytesIO()
    strm.write(buf, 0x1802FFFF)

    if gzipped:
        import gzip

        with open(out_stream_file_dir, "wb") as f:
            f.write(gzip.compress(buf.getvalue(), compresslevel=6))
    else:
        with open(out_stream_file_dir, "wb") as f:
            f.write(buf.getvalue())

