from collections.abc import Iterable, Iterator, Sized
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    MofNCompleteColumn,
    TimeRemainingColumn,
)
import re
from cyclopts import Parameter, validators
from typing import Annotated
from pathlib import Path

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

def sanitize_filename(file_name: str) -> str:
    """Make a filename valid on Windows."""
    return re.sub(r'[<>:"/\\|?*]', "_", file_name)

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
