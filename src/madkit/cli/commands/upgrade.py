import json
import shlex
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

from ..cli import app

MONOREPO_PACKAGES = ["madkit", "madformats", "madlysimple", "tfbpseudo", "tfbscript"]


def _installed_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in MONOREPO_PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass
    return versions


def _is_editable(name: str) -> bool:
    direct_url = metadata.distribution(name).read_text("direct_url.json")
    if not direct_url:
        return False
    return bool(json.loads(direct_url).get("dir_info", {}).get("editable", False))


def _require(executable: str) -> str:
    path = shutil.which(executable)
    if path is None:
        raise SystemExit(f"madkit was installed with {executable}, but {executable} is not on PATH.")
    return path


def _upgrade_command(packages: list[str]) -> list[str]:
    """Build the upgrade command for whichever package manager owns this environment."""
    prefix = Path(sys.prefix)

    # `uv tool install`: the tool environment is named after the tool.
    if (prefix / "uv-receipt.toml").is_file():
        return [_require("uv"), "tool", "upgrade", prefix.name]

    # `pipx install`: same idea, pip runs inside the pipx venv.
    if (prefix / "pipx_metadata.json").is_file():
        return [_require("pipx"), "runpip", prefix.name, "install", "--upgrade", *packages]

    installer = (metadata.distribution("madkit").read_text("INSTALLER") or "").strip()
    if installer == "uv":
        return [_require("uv"), "pip", "install", "--upgrade", "--python", sys.executable, *packages]

    return [sys.executable, "-m", "pip", "install", "--upgrade", *packages]


@app.command
def upgrade(dry_run: bool = False, verbose: bool = False):
    """Upgrade all installed madkit packages using the package manager they were installed with.

    Parameters
    ----------
    dry_run : bool
        Only print the command that would be run.
    verbose : bool
        Show the package manager's output.
    """
    before = _installed_versions()

    editable = [name for name in before if _is_editable(name)]
    packages = [name for name in before if name not in editable]

    if editable:
        print(f"Skipping editable installs (update them from source): {', '.join(editable)}")
    if not packages:
        print("Nothing to upgrade.")
        return

    command = _upgrade_command(packages)
    print(f"$ {shlex.join(command)}")
    if dry_run:
        return

    if verbose:
        result = subprocess.run(command, check=False)
    else:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if result.returncode != 0:
        if not verbose:
            print(result.stdout, end="")
        raise SystemExit(result.returncode)

    after = _installed_versions()
    for name in packages:
        old, new = before[name], after.get(name)
        if new is None:
            print(f"{name} {old} -> (removed)")
        elif old != new:
            print(f"{name} {old} -> {new}")
        else:
            print(f"{name} {old} (already up to date)")
