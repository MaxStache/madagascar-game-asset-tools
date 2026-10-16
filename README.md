# Madagascar Asset Tools

![Python >= 3.12](https://img.shields.io/badge/python-%3E%3D3.12-blue)

Loads `.stream .dff .txd .bsp .txl .rws .lpa`

`madkit` is a collection of tools for modding the game "Madagascar" (released in 2005): a CLI to unpack, repack and build mods for the game's level files, plus viewers for streams and textures.

## Contents

- [Requirements](#requirements)
- [Getting started](#getting-started)
  - [1. Create a modding folder](#1-create-a-modding-folder)
  - [2. Copy the stock levels](#2-copy-the-stock-levels)
  - [3. Configure madkit](#3-configure-madkit)
- [Mods](#mods)
- [CLI](#cli)
- [Tools](#tools)
- [Development](#development)

## Requirements

- [Python >= 3.12](https://www.python.org/downloads/)
- Your own copy of the game

> [!NOTE]
>
> ## 🎥 Video Tutorials
>
> **[▶️ Madagascar Modding Tutorials – YouTube Playlist](https://www.youtube.com/playlist?list=PLbBnMoHCtodg)**

## Getting started

### 1. Create a modding folder

Make a folder for your mods with its own virtual environment, and install `madkit` and `madlysimple` into it:

```bash
mkdir my-madagascar-mods
cd my-madagascar-mods
python -m venv .venv

# WINDOWS:
.venv\Scripts\activate
# LINUX/MACOS:
source .venv/bin/activate

pip install madkit madlysimple
```

`madkit` is the CLI and tools, `madlysimple` the helpers you use in your mod scripts.

The environment stays active until you close the terminal. In every new terminal, `cd` into your modding folder and run the `activate` line again before using `madkit`.

To update later: `pip install --upgrade madkit madlysimple`.

### 2. Copy the stock levels

Mods are built from the original `.stream` level files. Copy the game's `Levels/` folder into your modding folder:

```text
my-madagascar-mods/
  .venv/
  Levels/          # copy of <game folder>/Levels, never modified
```

> [!IMPORTANT]
> Keep this copy untouched. `madkit mod install` overwrites the levels in the game folder, so building from the game's own `Levels/` would stack mods on top of each other.

### 3. Configure madkit

Tell `madkit` where the game is installed (once):

```bash
madkit config --game-dir "C:/Games/Madagascar"
```

This writes a `settings.toml` in the current folder, so run `madkit` from your modding folder. Use `--levels-dir` if your stock levels are somewhere other than `Levels/`.

## Mods

Create a mod:

```bash
madkit mod init my_mod --level kingofny
```

This creates:

```text
mods/my_mod/
  mod.toml      # name, description
  build.py      # @level(...) functions
  assets/       # files the mod imports (.AI scripts, textures, ...)
```

Each `@level` function receives the named levels, loaded from `Levels/<level>.stream`.
After all functions ran, every level they received is saved to `mods/my_mod/build/<level>.stream`.

```python
from pathlib import Path

from madformats.mod import level
from madformats.stream import RW_StreamFile

ASSETS = Path(__file__).parent / "assets"

@level("kingofny")
def gold_coins(kingofny: RW_StreamFile) -> None:
    kingofny.assetByName("DG_Coin_Collectable.AI").importFrom(ASSETS / "scripts/DG_Coin_Collectable.AI")

@level("kingofny")          # stacked: runs once per level
@level("kingofny_regen")
def bigger_coins(lvl): ...

@level("street", "kingofny")  # several names: one call with all levels
def alex_to_marty(street, kingofny): ...
```

Build it, or build it and copy the levels into the game:

```bash
madkit mod build my_mod     # -> mods/my_mod/build/
madkit mod install my_mod   # build + copy into <game folder>/Levels
```

Back up the game's `Levels/` folder before installing mods, so you can restore the originals.

## CLI

```bash
madkit unpack LEVEL.stream output/directory/

madkit repack input/directory/ LEVEL.stream
```

For more information run

```bash
madkit --help
madkit COMMAND --help
```

## Tools

GUI tools are run as modules:

```bash
python -m madkit.tools.stream LEVEL.stream   # stream viewer
python -m madkit.tools.txd FILE.txd          # texture viewer
python -m madkit.tools.analyze FILE          # RenderWare file viewer
tfbeditor                                    # TfbPseudo AI script editor
```

## Development

To work on madkit itself you need [uv](https://docs.astral.sh/uv/getting-started/installation/). Clone the repository and install the whole workspace:

```bash
git clone https://github.com/MaxStache/madagascar-game-asset-tools.git
cd madagascar-game-asset-tools
uv sync
```

The repository is a uv workspace with these packages, all installed in editable mode:

| Package | Path | Import |
| --- | --- | --- |
| `madkit` (CLI + tools) | `src/madkit/` | `madkit.cli`, `madkit.tools.*` |
| `madformats` (file formats) | `packages/madformats/` | `madformats` |
| `madlysimple` (modding helpers) | `packages/madlysimple/` | `madlysimple` |
| `tfbpseudo` (AI script compiler + editor) | `packages/tfbpseudo/` | `tfbpseudo` |
| `tfbscript` (.ai parser/decompiler, `tfbtool`) | `packages/tfbscript/` | `tfbscript` |

Each package under `packages/` has its own `pyproject.toml` and is published to PyPI on its own.

## License

Apache-2.0. See [LICENSE](https://github.com/MaxStache/madagascar-game-asset-tools/blob/main/LICENSE).

## Disclaimer

Unofficial fan project, not affiliated with or endorsed by DreamWorks,
Activision or Toys for Bob. No game assets are included, you need your own copy of the game.
