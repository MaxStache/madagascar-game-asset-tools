"""Mod build scripts: mark level edits with ``@level(...)``.

    @level("kingofny")
    def gold_coins(kingofny): ...

    @level("kingofny")          # stacked: runs once per level, top to bottom
    @level("kingofny_regen")
    def bigger_coins(lvl): ...

    @level("street", "kingofny")  # several names: one call, all levels passed in
    def alex_to_marty(street, kingofny): ...

Every level a function receives is saved by ``cli mod build``.
"""

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Any

type LevelFunc = Callable[..., Any]

_REGISTRY: list[tuple[tuple[str, ...], LevelFunc]] = []  # [ ( names, func) ]


def level(*names: str) -> Callable[[LevelFunc], LevelFunc]:
    """Register a function that edits the named levels (passed in that order)."""
    if not names:
        raise ValueError("@level needs at least one level name")

    def decorator(fn: LevelFunc) -> LevelFunc:
        # Stacked decorators apply bottom-up; insert ahead of this function's
        # earlier entries so they run in the order they are written.
        idx = next((i for i, (_, f) in enumerate(_REGISTRY) if f is fn), len(_REGISTRY))
        _REGISTRY.insert(idx, (names, fn))
        return fn

    return decorator

def collect(build_py: Path) -> list[tuple[tuple[str, ...], LevelFunc]]:
    """Import a mod's build.py and return its ``@level`` entries in run order."""

    _REGISTRY.clear()

    spec = importlib.util.spec_from_file_location(
        f"_mod_{build_py.parent.name}", build_py
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {build_py}")

    spec.loader.exec_module(importlib.util.module_from_spec(spec))

    entries = list(_REGISTRY)
    
    _REGISTRY.clear()

    return entries
