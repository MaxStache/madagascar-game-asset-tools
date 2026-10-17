"""Bump a workspace package and everything in the workspace that depends on it.

    uv run scripts/bump.py madformats            # patch bump
    uv run scripts/bump.py madformats minor      # patch | minor | major
    uv run scripts/bump.py madformats --dry-run  # only show what would change

The named package gets the requested bump. Every workspace package that depends on
it, directly or transitively, gets its `>=` lower bound raised to the new version
and a patch bump of its own, because the changed requirement is part of its
published metadata. uv.lock is updated at the end.
"""

import argparse
import json
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def workspace_members() -> dict[str, Path]:
    """Map each workspace package name to its pyproject.toml."""
    root = tomllib.loads((ROOT / "pyproject.toml").read_text())
    paths = [ROOT / "pyproject.toml"]
    for pattern in root["tool"]["uv"]["workspace"]["members"]:
        paths += sorted(ROOT.glob(f"{pattern}/pyproject.toml"))
    return {tomllib.loads(p.read_text())["project"]["name"]: p for p in paths}


def requirement_names(pyproject: Path) -> set[str]:
    project = tomllib.loads(pyproject.read_text())["project"]
    reqs = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        reqs += extra
    return {re.match(r"[A-Za-z0-9._-]+", r).group().lower() for r in reqs}


def affected_packages(target: str, members: dict[str, Path]) -> list[str]:
    """The target plus everything that depends on it, in discovery order."""
    deps = {
        name: requirement_names(path) & members.keys() for name, path in members.items()
    }
    found = [target]
    for current in found:
        found += [
            name for name, d in deps.items() if current in d and name not in found
        ]
    return found


def uv_bump(package: str, kind: str, dry_run: bool) -> str:
    """Bump the version in pyproject.toml without relocking and return the new version."""
    cmd = [
        "uv",
        "version",
        "--bump",
        kind,
        "--package",
        package,
        "--frozen",
        "--output-format",
        "json",
    ]
    if dry_run:
        cmd.append("--dry-run")
    out = subprocess.run(
        cmd, cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    return json.loads(out)["version"]


def raise_lower_bounds(pyproject: Path, new_versions: dict[str, str]) -> list[str]:
    """Rewrite `"name>=x"` / `"name[extra]>=x"` requirements; return the changed names."""
    text = pyproject.read_text()
    changed = []
    for name, version in new_versions.items():
        pattern = re.compile(
            rf'(["\']){re.escape(name)}(\[[^\]]*\])?>=[^,;"\']+', re.IGNORECASE
        )
        text, count = pattern.subn(rf"\g<1>{name}\g<2>>={version}", text)
        if count:
            changed.append(name)
    pyproject.write_text(text)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("package")
    parser.add_argument(
        "kind", nargs="?", default="patch", choices=["patch", "minor", "major"]
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    members = workspace_members()
    if args.package not in members:
        parser.error(
            f"unknown package {args.package!r}, expected one of: {', '.join(members)}"
        )

    new_versions = {}
    for name in affected_packages(args.package, members):
        kind = args.kind if name == args.package else "patch"
        new_versions[name] = uv_bump(name, kind, args.dry_run)
        print(f"{name} => {new_versions[name]}")

    if args.dry_run:
        return

    for name, path in members.items():
        if changed := raise_lower_bounds(path, new_versions):
            print(f"  {path.relative_to(ROOT)}: raised {', '.join(changed)}")

    subprocess.run(["uv", "lock", "--quiet"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
