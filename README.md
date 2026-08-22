# Madagascar Asset Tools

![Python >= 3.12](https://img.shields.io/badge/python-%3E%3D3.12-blue)

Loads `.stream .dff .txd .bsp .bsp .txl .rws .lpa`

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

Restart your terminal after installation if necessary.

### 2. Clone the repository

```powershell
git clone <repository-url>
cd madagascar-game-asset-tools
```

### 3. Install dependencies

Run:

```powershell
uv sync
```

This automatically creates a virtual environment and installs the dependencies specified by the project.

### 4. Installing the folders as packages

```bash
uv add --editable ./madlysimple
uv add --editable ./madagascar
```

### 5. Running scripts with UV

You can run Python scripts through `uv` without manually activating the virtual environment:

```powershell
uv run python <script>.py
uv run python -m <module>
```

Alternatively, activate the virtual environment manually:

```powershell
.venv\Scripts\activate
```

## Usage

### CLI

```sh
uv run cli unpack LEVEL.stream output/directory/

uv run cli repack output/directory/ LEVEL.stream
```

For more information run

```sh
uv run cli --help
```
