from pathlib import Path

from ..cli import app
from ..settings import SETTINGS_FILE, load_settings, save_settings


@app.command
def config(game_dir: Path | None = None, levels_dir: Path | None = None):
    """Create or update settings.toml, then print it.

    Parameters
    ----------
    game_dir : Path
        Game install folder (the one containing Levels/).
    levels_dir : Path
        Folder with the stock .stream files that mods are built from.
    """
    settings = load_settings()
    if game_dir is not None:
        settings.game_dir = game_dir
    if levels_dir is not None:
        settings.levels_dir = levels_dir

    save_settings(settings)
    print(f"{SETTINGS_FILE.resolve()}:\n")
    print(settings.to_toml())
