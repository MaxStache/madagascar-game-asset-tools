import io
import json

from cyclopts import App, Parameter, validators
from typing import Annotated, Any, cast
from pathlib import Path
from formats.lib.rwConstants import strfunc_func
from formats.lib.rw_basics import RW_StreamFunc_NotImplemented
from formats.lib.zlib113 import gzip_compress
from formats.stream import RW_StreamFile, load_stream
from collections.abc import Iterable, Iterator, Sized
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    MofNCompleteColumn,
    TimeRemainingColumn,
)
import os

from formats.streamfuncs import STRFUNC_REGISTRY
from formats.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import RW_sf_LoadEmbeddedAsset


def progress[T](
    iterable: Iterable[T],
    description: str = "Processing...",
) -> Iterator[T]:
    total = len(iterable) if isinstance(iterable, Sized) else None

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
    ) as p:
        task = p.add_task(description, total=total)

        for item in iterable:
            yield item
            p.advance(task)


ValidatedExistingPath = Annotated[
    Path,
    Parameter(validator=validators.Path(exists=True)),
]
ValidatedExistingFile = Annotated[
    Path,
    Parameter(validator=validators.Path(exists=True, file_okay=True, dir_okay=False)),
]
ValidatedExistingDir = Annotated[
    Path,
    Parameter(validator=validators.Path(exists=True, file_okay=False, dir_okay=True)),
]
ValidatedDir = Annotated[
    Path,
    Parameter(validator=validators.Path(file_okay=False, dir_okay=True)),
]
ValidatedFile = Annotated[
    Path,
    Parameter(validator=validators.Path(file_okay=True, dir_okay=False)),
]

app = App(name="python -m cli")


def loadEmbeddedAssets_to_file_name(sec: RW_sf_LoadEmbeddedAsset) -> str:
    file_name = Path(sec.name).stem
    if sec.type == "rwID_TEXDICTIONARY":  # Texture Dictionary
        file_name += ".txd"
    elif sec.type == "rwaID_WAVEDICT":  # Wave Dictionary
        file_name += ".rws"
    elif sec.type == "rwID_WORLD":  # World
        file_name += ".bsp"
    elif sec.type == "TextStringDict":  # Text String Dict (Localization)
        file_name += ".txl"
    elif sec.type == "rwID_CLUMP":  # Clump (Model)
        file_name += ".dff"
    elif sec.type == "rwID_HANIMANIMATION":  # Bone Animation
        file_name += ".anm"
    elif sec.type == "SCRIPT":  # TFBScript
        file_name += ".ai"
    elif sec.type == "rwID_2DFONT":
        file_name += ".fnt"
    elif sec.type == "KFset":
        file_name += ".lpa"
    else:
        file_name += Path(sec.name).suffix

    return file_name


@app.command
def unpack(
    stream_file: ValidatedExistingFile,
    output_dir: ValidatedDir,
    readable: bool = False,
    gzipped: bool = False,
):
    """Unpack a stream files assets into a directory (including a manifest).

    Parameters
    ----------
    stream_file : str
        File to unpack.
    output_dir : str
        Directory to unpack the stream file into.
    readable : bool
        Whether to make the manifest more human-readable (pretty-printed).
    gzipped : bool
        Whether the stream file is gzipped or not.
    """

    strm = load_stream(stream_file, gzipped=gzipped)

    os.makedirs(output_dir, exist_ok=True)

    MANIFEST_FILE = Path(output_dir, "manifest.json")
    MANIFEST_CONTENTS: list[dict[str, Any]] = []

    for sec in progress(strm.contents, description="Processing..."):
        extra: dict[str, Any] = {}

        if sec.streamfunc == strfunc_func.sf_LoadEmbeddedAsset:
            sec = cast(RW_sf_LoadEmbeddedAsset, sec)

            base_file_name = loadEmbeddedAssets_to_file_name(sec)

            stem = Path(base_file_name).stem
            suffix = Path(base_file_name).suffix
            file_name = f"{stem}_{{{sec.guid}}}{suffix}"

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
        if readable:
            json.dump(MANIFEST_CONTENTS, f, indent=4)
        else:
            json.dump(MANIFEST_CONTENTS, f)


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
        with open(out_stream_file_dir, "wb") as f:
            f.write(gzip_compress(buf.getvalue()))
    else:
        with open(out_stream_file_dir, "wb") as f:
            f.write(buf.getvalue())


if __name__ == "__main__":
    app()
