# Madagascar Asset Tools

![Python >= 3.12](https://img.shields.io/badge/python-%3E%3D3.12-blue)

Loads `.stream .dff .txd .bsp .txl .rws .lpa`

This repo is a collection of tools used for modding the game "Madagascar" (released in 2005).

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
  - [1. Install uv](#1-install-uv)
  - [2. Clone the repository](#2-clone-the-repository)
  - [3. Install dependencies](#3-install-dependencies)
  - [4. Running scripts with UV](#4-running-scripts-with-uv)
- [Usage](#usage)
  - [CLI](#cli)

## Requirements

- [Python >= 3.12](https://www.python.org/downloads/)
- [uv package manager installed](https://docs.astral.sh/uv/getting-started/installation/)

## Installation

### 1. Install uv

If you don't already have `uv`, install it from the official documentation:

<https://docs.astral.sh/uv/getting-started/installation/>

Restart your terminal / vscode after installation if necessary.

### 2. Clone the repository

```bash
git clone https://github.com/MaxStache/madagascar-game-asset-tools.git
cd madagascar-game-asset-tools
```

### 3. Install dependencies

Run:

```bash
uv sync
```

This automatically creates a virtual environment and installs the dependencies specified by the project.

### 4. Running scripts with UV

You can run Python scripts through `uv` without manually activating the virtual environment:

```bash
uv run python <script>.py
uv run python -m <module>
```

Alternatively, activate the virtual environment manually:

```bash
WINDOWS:
.venv\Scripts\activate
LINUX/MACOS:
.venv/bin/activate
```

## Usage

### CLI

```bash
uv run cli unpack LEVEL.stream output/directory/

uv run cli repack input/directory/ LEVEL.stream
```

For more information run

```bash
uv run cli --help
```

## Related

- [madagascar-tfbtool](https://github.com/MaxStache/madagascar-tfbtool) —
  parser and decompiler for the game's TFB script files (`.ai`).

## License

Apache-2.0. See [LICENSE](LICENSE).

## Disclaimer

Unofficial fan project, not affiliated with or endorsed by DreamWorks,
Activision or Toys for Bob. No game assets are included — you need your own
copy of the game.
