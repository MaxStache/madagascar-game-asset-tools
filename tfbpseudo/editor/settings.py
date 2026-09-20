"""What the editor remembers between runs.

Two things, both about getting back to work: the files opened lately, and
where each source was last compiled to. Neither is worth a file of its own, so
they go where Qt puts this sort of thing -- the registry on Windows, a config
file elsewhere -- through QSettings.

Paths are kept as text exactly as they were given. A remembered path is a
guess about the world, so everything here hands back what it stored and lets
the caller find out whether it is still true.
"""

# pyright: basic

import json
from pathlib import Path

from PySide6.QtCore import QSettings

ORGANISATION = "tfbpseudo"
APPLICATION = "editor"

RECENT = "recent"
BUILDS = "builds"

MOST_RECENT = 8  # how many files the menu lists


def store() -> QSettings:
    return QSettings(ORGANISATION, APPLICATION)


def recent() -> list[str]:
    """The files opened lately, newest first."""
    kept = store().value(RECENT, [])

    # A single-entry list comes back as a bare string on some backends.
    if isinstance(kept, str):
        return [kept]

    return [str(path) for path in kept] if kept else []


def remember_opened(path: Path | str) -> list[str]:
    """Put `path` at the front of the recent list and return the new list."""
    text = str(Path(path))
    kept = [other for other in recent() if other != text]
    kept.insert(0, text)
    del kept[MOST_RECENT:]

    store().setValue(RECENT, kept)
    return kept


def forget_recent() -> None:
    store().setValue(RECENT, [])


def builds() -> dict[str, str]:
    """Where each source was last compiled to, by source path.

    Kept as one JSON string rather than a key each, because a Windows path is
    full of the separators QSettings reads as its own.
    """
    try:
        kept = json.loads(store().value(BUILDS, "{}") or "{}")
    except (TypeError, ValueError):
        return {}

    return kept if isinstance(kept, dict) else {}


def build_target(source: Path | str | None) -> Path | None:
    """Where `source` was last compiled to, if it has been."""
    if source is None:
        return None

    target = builds().get(str(Path(source)))
    return Path(target) if target else None


def remember_build(source: Path | str | None, target: Path | str) -> None:
    """Note that `source` was compiled to `target`, for the next time."""
    if source is None:
        return

    kept = builds()
    kept[str(Path(source))] = str(Path(target))
    store().setValue(BUILDS, json.dumps(kept))
