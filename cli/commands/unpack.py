from enum import Enum

from ..cli import app
from ..utils import (
    ValidatedExistingFile,
    ValidatedDir,
    progress,
    loadEmbeddedAssets_to_file_name,
    sanitize_filename,
)
from madagascar.stream import load_stream
from madagascar.lib.rwConstants import strfunc_func
import json
import os
from pathlib import Path
from typing import Any, cast
from madagascar.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import RW_sf_LoadEmbeddedAsset


class FileNaming(Enum):
    GUID = 0
    SEC_IDX = 1


@app.command
def unpack(
    stream_file: ValidatedExistingFile,
    output_dir: ValidatedDir,
    naming: FileNaming = FileNaming.SEC_IDX,
    human: bool = True,
    gzipped: bool = False,
):
    """Unpack a stream files assets into a directory (including a manifest).

    Parameters
    ----------
    stream_file : str
        File to unpack.
    output_dir : str
        Directory to unpack the stream file into.
    human : bool
        Whether to make the manifest more human-readable (pretty-printed).
    gzipped : bool
        Whether the stream file is gzipped or not.
    """

    strm = load_stream(stream_file, gzipped=gzipped)

    os.makedirs(output_dir, exist_ok=True)

    MANIFEST_FILE = Path(output_dir, "manifest.json")
    MANIFEST_CONTENTS: list[dict[str, Any]] = []

    enumerated_contents = enumerate(strm.contents)
    for i, sec in progress(
        enumerate(strm.contents),
        description="Processing...",
        total=len(list(enumerated_contents)),
    ):
        extra: dict[str, Any] = {}

        if sec.streamfunc == strfunc_func.sf_LoadEmbeddedAsset:
            sec = cast(RW_sf_LoadEmbeddedAsset, sec)

            base_file_name = loadEmbeddedAssets_to_file_name(sec)

            stem = Path(base_file_name).stem
            suffix = Path(base_file_name).suffix

            if naming == FileNaming.GUID:
                file_name = f"{stem}_{{{sec.guid}}}{suffix}"

            elif naming == FileNaming.SEC_IDX:
                file_name = f"{i}_{stem}{suffix}"

            file_name = sanitize_filename(file_name)

            with open(Path(output_dir, file_name), "wb") as f:
                f.write(sec.data)

            extra["file_name"] = file_name

        sec_dict = sec.to_dict()
        MANIFEST_CONTENTS.append(
            {
                "streamfunc": sec.streamfunc.name if sec.streamfunc else None,
                **sec_dict,
                **extra,
            }
        )

    with open(MANIFEST_FILE, "w") as f:
        if human:
            json.dump(MANIFEST_CONTENTS, f, indent=4)
        else:
            json.dump(MANIFEST_CONTENTS, f)
