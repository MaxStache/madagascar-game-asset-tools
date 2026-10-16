# tfbpseudo

Compiler and decompiler for **TfbPseudo**, a readable text form of the AI scripts (`.ai` files) in *Madagascar* (2005, PC).

Decompile a script to text, edit it, and compile it back to a byte-compatible `.ai` file. The binary format itself is handled by [`tfbscript`](https://pypi.org/project/tfbscript/).

```bash
pip install tfbpseudo            # compiler + decompiler
pip install "tfbpseudo[editor]"  # plus the Qt editor (tfbeditor)
```

```python
from tfbscript import ScriptFile
from tfbpseudo import compile_source, decompile_script

source = decompile_script(ScriptFile.from_path("DG_Coin_Collectable.ai"))
# ... edit source ...
script = compile_source(source)
with open("DG_Coin_Collectable.ai", "wb") as f:
    script.write(f)
```

With the `editor` extra installed, `tfbeditor [FILE]` opens a TfbPseudo editor with syntax highlighting and completion.

Part of the [madagascar-game-asset-tools](https://github.com/MaxStache/madagascar-game-asset-tools) monorepo.
