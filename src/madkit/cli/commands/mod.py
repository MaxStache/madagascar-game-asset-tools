import shutil
import tomllib
from pathlib import Path

import cyclopts

from ..cli import app
from ..settings import load_settings
from madformats.mod import collect
from madformats.stream import RW_StreamFile, load_stream

MODS_DIR = Path("mods")

mod_app = cyclopts.App(name="mod", help="Create, build and install mods.")
app.command(mod_app)

MOD_TOML_TEMPLATE = """\
name = "{name}"
description = ""
"""

BUILD_PY_TEMPLATE = """\
from pathlib import Path

from madformats.mod import level
from madformats.stream import RW_StreamFile

ASSETS = Path(__file__).parent / "assets"


@level("{level}")
def edit_{level}({level}: RW_StreamFile) -> None:
    # =================================

    # YOUR MODDING CODE HERE ;)

    # =================================
    pass
"""


def _mod_dir(name: str) -> Path:
    mod_dir = MODS_DIR / name
    if not (mod_dir / "build.py").is_file():
        raise SystemExit(f"No mod at {mod_dir} (missing build.py)")
    return mod_dir


@mod_app.command
def init(name: str, level: str = "kingofny"):
    """Create a new mod folder from the template.

    Parameters
    ----------
    name : str
        Mod name, becomes the folder mods/NAME.
    level : str
        Level the template's first @level function edits.
    """
    mod_dir = MODS_DIR / name
    if mod_dir.exists():
        raise SystemExit(f"{mod_dir} already exists")

    (mod_dir / "assets").mkdir(parents=True)
    (mod_dir / "mod.toml").write_text(MOD_TOML_TEMPLATE.format(name=name))
    (mod_dir / "build.py").write_text(BUILD_PY_TEMPLATE.format(level=level))
    print(f"Created {mod_dir}")


def _build(name: str) -> list[Path]:
    mod_dir = _mod_dir(name)
    with open(mod_dir / "mod.toml", "rb") as f:
        manifest = tomllib.load(f)

    entries = collect(mod_dir / "build.py")
    if not entries:
        raise SystemExit(f"{mod_dir / 'build.py'} has no @level functions")

    levels_dir = load_settings().levels_dir
    levels: dict[str, RW_StreamFile] = {}
    for names, _ in entries:
        for level_name in names:
            if level_name not in levels:
                levels[level_name] = load_stream(levels_dir / f"{level_name}.stream")

    for names, fn in entries:
        print(f"{fn.__name__}({', '.join(names)})")
        fn(*(levels[n] for n in names))

    out_dir = mod_dir / "build"
    out_dir.mkdir(exist_ok=True)
    written: list[Path] = []
    for level_name, strm in levels.items():
        strm.updatePlacementNew()
        strm.verify()
        out_file = out_dir / f"{level_name}.stream"
        strm.save(out_file)
        written.append(out_file)

    print(f"Built {manifest.get('name', name)}: {', '.join(str(p) for p in written)}")
    return written


@mod_app.command
def build(name: str):
    """Run a mod's @level functions and write the levels to mods/NAME/build/.

    Parameters
    ----------
    name : str
        Mod name (folder in mods/).
    """
    _build(name)


@mod_app.command
def install(name: str, game_dir: Path | None = None):
    """Build a mod and copy its levels into the game's Levels folder.

    Parameters
    ----------
    name : str
        Mod name (folder in mods/).
    game_dir : Path
        Game install folder (the one containing Levels/). Defaults to game_dir in settings.toml.
    """
    if game_dir is None:
        game_dir = load_settings().game_dir
        if game_dir is None:
            raise SystemExit("Pass --game-dir or run: madkit config --game-dir PATH")

    game_levels = game_dir / "Levels"
    if not game_levels.is_dir():
        raise SystemExit(f"{game_levels} does not exist")

    for built in _build(name):
        shutil.copy2(built, game_levels / built.name)
        print(f"Installed {game_levels / built.name}")
