import io
import json
import shutil
import time
import tomllib
from collections.abc import Callable, Hashable, Iterable
from pathlib import Path
import hashlib

import cyclopts
from madformats.lib.parser import Parser
from madformats.lib.rwConstants import DEFAULT_VERSION_STAMP
from madformats.lib.rw_basics import RW_Matrix4x4, RW_StreamFunc

from ..cli import app
from ..settings import load_settings
from ..utils import ValidatedExistingFile
from madformats.mod import collect
from madformats.stream import RW_StreamFile, load_stream
from madformats.streamfuncs.stringfuncs.sf_CreateEntity import (
    RW_sf_CreateEntity,
    RW_sf_CreateEntity_Attribute,
)
from madformats.streamfuncs.stringfuncs.sf_LoadEmbeddedAsset import (
    RW_sf_LoadEmbeddedAsset,
)
from colorama import init as colorama_init
from colorama import Fore

MODS_DIR = Path("mods")

mod_app = cyclopts.App(name="mod", help="Create, build and install mods.")
app.command(mod_app)

colorama_init(True)

MOD_TOML_TEMPLATE = """\
name = "{name}"
description = ""
version = "0.0.0"
"""

BUILD_PY_TEMPLATE = """\
from pathlib import Path

from madformats.mod import level
from madformats.stream import RW_StreamFile

ASSETS = Path(__file__).parent / "assets"

@level("{level}")
def edit_{level}({level}: RW_StreamFile) -> None:
    # You can now do modifications on `{level}` in here, they will be saved automatically when build
    pass
"""


def _mod_dir(name: str) -> Path:
    mod_dir = MODS_DIR / name
    if not (mod_dir / "build.py").is_file():
        raise SystemExit(f"No mod at {mod_dir} (missing build.py)")
    return mod_dir


@mod_app.command
def init(name: str, level: str = "kingofny"):
    """Create a new mod folder from the template.

    Parameters
    ----------
    name : str
        Mod name, becomes the folder mods/NAME.
    level : str
        Level the template's first @level function edits.
    """
    mod_dir = MODS_DIR / name
    if mod_dir.exists():
        raise SystemExit(f"{mod_dir} already exists")

    (mod_dir / "assets").mkdir(parents=True)
    (mod_dir / "mod.toml").write_text(MOD_TOML_TEMPLATE.format(name=name))
    (mod_dir / "build.py").write_text(BUILD_PY_TEMPLATE.format(level=level))
    print(f"Created {mod_dir}")


def _build(name: str, verbose: bool = False) -> list[Path]:
    start = time.perf_counter()
    mod_dir = _mod_dir(name)
    with open(mod_dir / "mod.toml", "rb") as f:
        manifest = tomllib.load(f)
    mod_name = manifest.get("name", name)

    print(f"[MOD] building {mod_name}")

    entries = collect(mod_dir / "build.py")
    if not entries:
        raise SystemExit(f"{mod_dir / 'build.py'} has no @level functions")

    levels_dir = load_settings().levels_dir
    levels: dict[str, RW_StreamFile] = {}
    for names, _ in entries:
        for level_name in names:
            if level_name not in levels:
                levels[level_name] = load_stream(levels_dir / f"{level_name}.stream")

    for names, fn in entries:
        print(f"[MOD] run {fn.__name__}({', '.join(names)})")
        fn(*(levels[n] for n in names))

    BUILD_OUTPUTS: list[tuple[str, str]] = []

    out_dir = mod_dir / "build"
    out_dir.mkdir(exist_ok=True)
    written: list[Path] = []
    for level_name, strm in levels.items():
        strm.updatePlacementNew()
        strm.verify(label=level_name, verbose=verbose)
        out_file = out_dir / f"{level_name}.stream"

        strmBytes = strm.toBytes(DEFAULT_VERSION_STAMP)
        with open(out_file, "wb") as f:
            f.write(strmBytes)

        written.append(out_file)
        print(f"[MOD] wrote {out_file}")

        BUILD_OUTPUTS.append(
            (f"{level_name}.stream", hashlib.sha256(strmBytes).hexdigest())
        )

    with open(out_dir / "build.json", "w") as f:
        json.dump(
            {
                "output": [
                    {
                        "name": b[0],
                        "sha265": b[1],
                    }
                    for b in BUILD_OUTPUTS
                ]
            },
            f,
            indent=4,
        )

    print(
        Fore.LIGHTCYAN_EX
        + f"[MOD] built {mod_name} (took: {time.perf_counter() - start:.2f}s)"
    )
    return written


@mod_app.command
def build(name: str, verbose: bool = False):
    """Run a mod's @level functions and write the levels to mods/NAME/build/.

    Parameters
    ----------
    name : str
        Mod name (folder in mods/).
    """
    _build(name, verbose)


@mod_app.command
def install(name: str, game_dir: Path | None = None):
    """Build a mod and copy its levels into the game's Levels folder.

    Parameters
    ----------
    name : str
        Mod name (folder in mods/).
    game_dir : Path
        Game install folder (the one containing Levels/). Defaults to game_dir in settings.toml.
    """
    if game_dir is None:
        game_dir = load_settings().game_dir
        if game_dir is None:
            raise SystemExit("Pass --game-dir or run: madkit config --game-dir PATH")

    game_levels = game_dir / "Levels"
    if not game_levels.is_dir():
        raise SystemExit(f"{game_levels} does not exist")

    for built in _build(name):
        shutil.copy2(built, game_levels / built.name)
        print(f"Installed {game_levels / built.name}")


# region === Diff ===

# (header, line): header groups lines under an entity/asset, None for top-level changes
Change = tuple[str | None, str]
Key = tuple[Hashable, int]
AttrKey = tuple[str, int, int, int]


def _keyed[T](items: Iterable[T], key: Callable[[T], Hashable]) -> dict[Key, T]:
    """Index items by (key, occurrence) so duplicate keys still pair up in order."""
    seen: dict[Hashable, int] = {}
    out: dict[Key, T] = {}
    for item in items:
        k = key(item)
        n = seen.get(k, 0)
        seen[k] = n + 1
        out[(k, n)] = item
    return out


def _fmt_matrix(m: RW_Matrix4x4) -> str:
    rows = (m.row1, m.row2, m.row3)
    rot = " | ".join(f"{r.x:.3g} {r.y:.3g} {r.z:.3g}" for r in rows)
    return f"pos=({m.row4.x:.3f}, {m.row4.y:.3f}, {m.row4.z:.3f}) rot=[{rot}]"


def _fmt_attr(class_name: str, attr: RW_sf_CreateEntity_Attribute) -> str:
    data = attr.data

    if class_name == "CSystemCommands" and attr.command == 0x01 and len(data) >= 64:
        return _fmt_matrix(RW_Matrix4x4.read(Parser(data)))

    if len(data) >= 42 and data[4:5] == b"{":
        try:
            ref = attr.asTfbRef()
            return f"ref {ref.guid}" + (f" {ref.name!r}" if ref.name else "")
        except Exception:
            pass

    text = data.replace(b"\xbf", b"").rstrip(b"\x00")
    if text and all(32 <= c < 127 for c in text):
        return repr(text.decode("latin1"))

    if len(data) > 24:
        return f"{data[:24].hex(' ')} ... ({len(data)} bytes)"
    return data.hex(" ") or "<empty>"


def _attr_map(
    entity: RW_sf_CreateEntity,
) -> dict[AttrKey, tuple[str, RW_sf_CreateEntity_Attribute]]:
    out: dict[AttrKey, tuple[str, RW_sf_CreateEntity_Attribute]] = {}
    for (_, cls_n), cls in _keyed(entity.classes, lambda c: c.class_name).items():
        for (_, cmd_n), attr in _keyed(cls.attributes, lambda a: a.command).items():
            out[(cls.class_name, cls_n, attr.command, cmd_n)] = (cls.class_name, attr)
    return out


def _entity_label(entity: RW_sf_CreateEntity) -> str:
    return (
        f"{entity.getDisplayName()} [{entity.behaviour or '?'}] {{{entity.entityID}}}"
    )


def _diff_entities(a: RW_StreamFile, b: RW_StreamFile) -> list[Change]:
    changes: list[Change] = []
    ents_a = _keyed(a.entities(), lambda e: e.entityID)
    ents_b = _keyed(b.entities(), lambda e: e.entityID)

    for key, ea in ents_a.items():
        eb = ents_b.get(key)
        if eb is None:
            changes.append((None, Fore.LIGHTRED_EX + f"- entity {_entity_label(ea)}"))
            continue

        header = Fore.LIGHTYELLOW_EX + f"~ entity {_entity_label(eb)}"
        if ea.behaviour != eb.behaviour:
            changes.append(
                (header, f"    behaviour: {ea.behaviour!r} -> {eb.behaviour!r}")
            )
        if ea.isGlobal != eb.isGlobal:
            changes.append((header, f"    isGlobal: {ea.isGlobal} -> {eb.isGlobal}"))

        attrs_a, attrs_b = _attr_map(ea), _attr_map(eb)
        for akey in list(attrs_a) + [k for k in attrs_b if k not in attrs_a]:
            cls_name, _, cmd, _ = akey
            where = f"{cls_name}[{cmd:#x}]"
            old, new = attrs_a.get(akey), attrs_b.get(akey)
            if old is not None and new is None:
                changes.append(
                    (header, Fore.LIGHTRED_EX + f"    - {where}: {_fmt_attr(*old)}")
                )
            elif old is None and new is not None:
                changes.append(
                    (header, Fore.LIGHTGREEN_EX + f"    + {where}: {_fmt_attr(*new)}")
                )
            elif old is not None and new is not None and old[1].data != new[1].data:
                changes.append(
                    (header, f"    ~ {where}: {_fmt_attr(*old)} -> {_fmt_attr(*new)}")
                )

    for key, eb in ents_b.items():
        if key not in ents_a:
            changes.append((None, Fore.LIGHTGREEN_EX + f"+ entity {_entity_label(eb)}"))

    return changes


def _diff_assets(a: RW_StreamFile, b: RW_StreamFile) -> list[Change]:
    changes: list[Change] = []
    assets_a = _keyed(a.embeddedAssets(), lambda x: x.guid)
    assets_b = _keyed(b.embeddedAssets(), lambda x: x.guid)

    def label(asset: RW_sf_LoadEmbeddedAsset) -> str:
        return f"{asset.name} [{asset.type}] {{{asset.guid}}}"

    for key, xa in assets_a.items():
        xb = assets_b.get(key)
        if xb is None:
            changes.append((None, Fore.LIGHTRED_EX + f"- asset {label(xa)}"))
            continue

        header = Fore.LIGHTYELLOW_EX + f"~ asset {label(xb)}"
        for field_name in ("name", "type", "filePath", "deps"):
            old, new = getattr(xa, field_name), getattr(xb, field_name)
            if old != new:
                changes.append((header, f"    {field_name}: {old!r} -> {new!r}"))
        if xa.data != xb.data:
            changes.append(
                (header, f"    data: {len(xa.data)} -> {len(xb.data)} bytes")
            )

    for key, xb in assets_b.items():
        if key not in assets_a:
            changes.append((None, Fore.LIGHTGREEN_EX + f"+ asset {label(xb)}"))

    return changes


def _diff_other(a: RW_StreamFile, b: RW_StreamFile) -> list[Change]:
    """Every other stream function, paired by type and position."""
    changes: list[Change] = []

    def others(strm: RW_StreamFile) -> dict[Key, RW_StreamFunc]:
        funcs = (
            sf
            for sf in strm.contents
            if not isinstance(sf, (RW_sf_CreateEntity, RW_sf_LoadEmbeddedAsset))
        )
        return _keyed(
            funcs, lambda sf: sf.streamfunc.name if sf.streamfunc else type(sf).__name__
        )

    def raw(sf: RW_StreamFunc) -> bytes:
        buf = io.BytesIO()
        sf.write(buf, DEFAULT_VERSION_STAMP)
        return buf.getvalue()

    others_a, others_b = others(a), others(b)
    for key in list(others_a) + [k for k in others_b if k not in others_a]:
        name, n = key
        name = str(name)
        fa, fb = others_a.get(key), others_b.get(key)
        if fb is None:
            changes.append((None, Fore.LIGHTRED_EX + f"- {name} #{n}"))
        elif fa is None:
            changes.append((None, Fore.LIGHTGREEN_EX + f"+ {name} #{n}"))
        else:
            ra, rb = raw(fa), raw(fb)
            if ra != rb:
                changes.append(
                    (
                        None,
                        Fore.LIGHTYELLOW_EX
                        + f"~ {name} #{n}: {len(ra)} -> {len(rb)} bytes",
                    )
                )

    return changes


@mod_app.command
def diff(a: ValidatedExistingFile, b: ValidatedExistingFile, max_changes: int = 100):
    """Show what changed between two .stream files (entities, assets, other stream functions).

    Parameters
    ----------
    a : Path
        Original .stream file.
    b : Path
        Modified .stream file.
    max_changes : int
        Stop printing after this many changes, 0 shows all.
    """
    strm_a, strm_b = load_stream(a), load_stream(b)
    changes = (
        _diff_entities(strm_a, strm_b)
        + _diff_assets(strm_a, strm_b)
        + _diff_other(strm_a, strm_b)
    )

    shown = changes if max_changes <= 0 else changes[:max_changes]
    last_header = None
    for header, line in shown:
        if header is not None and header != last_header:
            print(header)
        last_header = header
        print(line)

    if not changes:
        print(Fore.LIGHTCYAN_EX + "[DIFF] no changes")
    elif len(shown) < len(changes):
        print(
            Fore.LIGHTCYAN_EX
            + f"[DIFF] {len(changes)} changes, {len(changes) - len(shown)} not shown (raise --max-changes)"
        )
    else:
        print(Fore.LIGHTCYAN_EX + f"[DIFF] {len(changes)} changes")


# endregion
