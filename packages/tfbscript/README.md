# Madagascar TFBTool
 (uses outdated assumpsions about tfbscript)
Parser and decompiler for TFB script (`.ai`) files, as used by *Madagascar - The Game* (2005).

![Python >= 3.12](https://img.shields.io/badge/python-%3E%3D3.12-blue)

## Contents

- [Requirements](#requirements)
- [Usage](#usage)
- [Opcode coverage](#opcode-coverage)
- [Contributing](#contributing)
- [Thanks](#thanks)

## Requirements

- Python >= 3.12 (uses `typing.override`, added in 3.12)
- UV package manager
- Dependencies from `pyproject.toml`: `uv sync`

## Usage

### CLI

```sh
python -m tfbscript example_scripts/Teleporter.ai
python -m tfbscript --no-color example_scripts/*.ai
```

Syntax coloring is auto-detected: on for a real terminal, off when piped or
when `NO_COLOR` is set. Force it with `--color` / `--no-color`.

### As a library

```python
from tfbscript import ScriptFile

script = ScriptFile.from_path("example_scripts/Teleporter.ai")
script.print_tree()
```

## Thanks

A HUGE thanks to the Skylanders reverse engineering Discord server and its members, especially maff, bone and nefarioustechsupport.

Another GIGANTIC ENORMOUS thanks to all the contributors to igRewrite8, and to [this fork](https://github.com/bonesinmysoup/igRewrite8/tree/trapteam-but-real).

## Opcode coverage

**36 / 36 opcodes implemented**.

- [x] comment
- [x] print
- [x] if/else
- [x] for each
- [x] loop value
- [x] create variable
- [x] find variable
- [x] set reference
- [x] check reference
- [x] set value
- [x] check value
- [x] inc value
- [x] dec value
- [x] slide value
- [x] spawn actor
- [x] teleport to
- [x] move to
- [x] move from
- [x] displace
- [x] turn to
- [x] reset
- [x] play animation
- [x] play sound
- [x] stop sound
- [x] cut-scene
- [x] check message
- [x] send message
- [x] set behavior
- [x] check fov
- [x] control
- [x] run as player
- [x] find subset
- [x] check membership
- [x] change membership
- [x] use camera
- [x] remove

### Needs attention / TODOs

- `spawn actor::op-code` - find out purpose of remaining byte
- `displace::op-code` - confirm fields

## Contributing

Contributions as issues, pull requests, or any other form are welcome and wanted.

Please run `pytest` after changes to verify against all scripts in `example_scripts/`, and `pyright` for type checking.
