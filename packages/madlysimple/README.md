# madlysimple

Higher-level helpers for modding *Madagascar* (2005, PC), built on top of [`madformats`](https://pypi.org/project/madformats/).

`madformats` exposes the raw RenderWare structures. `madlysimple` wraps them in objects that are easier to mod with: level streams, actors (`CProtoActor`) and their parameter blocks, camera data, the level hub, and prefabs.

```bash
pip install madlysimple
```

```python
from madlysimple import LevelStream

level = LevelStream.load("Levels/kingofny.stream")
```

Part of the [madagascar-game-asset-tools](https://github.com/MaxStache/madagascar-game-asset-tools) monorepo.
