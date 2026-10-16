from pathlib import Path

import pytest

from madkit.cli.settings import load_settings

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def levels_dir() -> Path:
    """The stock Levels/ folder from settings.toml. Skips the test when it is missing."""
    levels = load_settings().levels_dir
    if not levels.is_absolute():
        levels = ROOT / levels
    if not levels.is_dir():
        pytest.skip(f"game data not found at {levels}")
    return levels


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # Tests marked `gamedata` get the Levels/ check without asking for the fixture.
    for item in items:
        if item.get_closest_marker("gamedata") and "levels_dir" not in item.fixturenames:
            item.fixturenames.append("levels_dir")
