# madformats

Read, edit and write the file formats of *Madagascar* (2005, PC), a RenderWare game.

Covers `.stream` level files, RenderWare models (`.dff`, `.bsp`), animations (`.anm`), texture dictionaries (`.txd`), audio (`.rws`) and save games.

```bash
pip install madformats
```

```python
from madformats.stream import RW_StreamFile

level = RW_StreamFile.load("Levels/kingofny.stream")
level.assetByName("DG_Coin_Collectable.AI").importFrom("my_script.AI")
level.save("kingofny.stream")
```

Part of the [madagascar-game-asset-tools](https://github.com/MaxStache/madagascar-game-asset-tools) monorepo. See also `madkit` (CLI), `madlysimple` (higher-level modding helpers), `tfbscript` and `tfbpseudo` (AI scripts).
