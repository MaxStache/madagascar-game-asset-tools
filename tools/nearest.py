"""List the live entities closest to the player, straight out of Game.exe's memory.

No .stream file needed - everything is derived from the process itself. Walks the
global entity list (head 0x0062fea8, uuid at +0x08, next at +0x18, same as
tools/livescan.py) and reads each node's world matrix at +0x148, translation at
+0x178.

That offset is only valid for classes that actually store a transform there, so
instead of trusting it blindly the script groups nodes by their vtable pointer
(+0x00, one per behaviour) and keeps a group only if its matrices really look
like transforms: rows unit-length and mutually perpendicular, translation finite,
and more than one distinct non-zero position in the group. In banquet that keeps
CProtoActor (425/425 nodes pass) and rejects every other class outright (0% pass)
- CTFBModel/SpriteObject/CTFBSound/CameraData nodes hold no transform there, and
CTFBModel entities are asset templates parked at the origin anyway.

Entity names are NOT in memory (the loader discards them - a full 357 MB scan of
the process finds no name string), so rows are identified by uuid unless you pass
--stream, which loads a level file purely to attach names to uuids.

    python tools/nearest.py [-n 20] [--all-classes] [--stream FILE] [--watch]
"""
import argparse
import math
import os
import struct
import sys
import time

import pymem

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from livescan import IMAGE_BASE, ENTITY_LIST_HEAD, walk  # noqa: E402

OFF_VTABLE = 0x00
OFF_MATRIX = 0x148
OFF_POS = OFF_MATRIX + 0x30   # 0x178, row 4 of the matrix

# Only for labelling - membership is decided by the matrix test, not this table.
KNOWN_VTABLES = {
    0x005CDBBC: "CProtoActor",
    0x005CCA84: "CTFBSound",
    0x005CBF3C: "SpriteObject",
    0x005D4E5C: "CTFBModel",
    0x005CCFD8: "CameraData",
    0x005CB514: "CFXPartSpray",
    0x005CAF70: "CFXColorLight",
    0x005CB5A4: "CFXMotionBlur",
    0x005D4D38: "RadarRender",
    0x005D4D9C: "ShadowRender",
    0x005CD12C: "TFBShadowCamera",
    0x005CD084: "GameCamera",
    0x005CBD48: "SpriteManager",
    0x005CCB4C: "CTFBWorld",
    0x005CCAD0: "LevelHub",
}

DEFAULT_CLASSES = ("CProtoActor",)

ROW_LENGTH_TOLERANCE = 0.1    # how far a matrix row may stray from unit length
ORTHOGONALITY_TOLERANCE = 0.05
MAX_COORDINATE = 1e6
MIN_SPATIAL_RATIO = 0.8       # share of a class's nodes that must pass the test
MIN_DISTINCT_POSITIONS = 2    # a class parked entirely at the origin is not spatial


def read_matrix(pm, addr):
    try:
        return struct.unpack("<16f", pm.read_bytes(addr + OFF_MATRIX, 64))
    except Exception:
        return None


def is_transform(matrix):
    """True if these 16 floats are a real world matrix, not whatever else lives there."""
    if matrix is None or not all(math.isfinite(v) for v in matrix):
        return False

    rows = (matrix[0:3], matrix[4:7], matrix[8:11])
    for row in rows:
        length = math.sqrt(sum(c * c for c in row))
        if abs(length - 1.0) > ROW_LENGTH_TOLERANCE:
            return False

    def dot(a, b):
        return sum(u * v for u, v in zip(a, b))

    if abs(dot(rows[0], rows[1])) > ORTHOGONALITY_TOLERANCE:
        return False
    if abs(dot(rows[0], rows[2])) > ORTHOGONALITY_TOLERANCE:
        return False

    return all(abs(c) < MAX_COORDINATE for c in matrix[12:15])


def translation(matrix):
    return (matrix[12], matrix[13], matrix[14])


def label_for(vtable_va):
    return KNOWN_VTABLES.get(vtable_va, f"vt_{vtable_va:08x}")


def group_by_class(pm, nodes, base):
    """{label: [(addr, uuid_bytes, matrix_or_None), ...]} keyed by vtable identity."""
    groups = {}
    for addr, raw in nodes:
        try:
            vtable = pm.read_uint(addr + OFF_VTABLE)
        except Exception:
            continue
        label = label_for(vtable - base + IMAGE_BASE)
        groups.setdefault(label, []).append((addr, raw, read_matrix(pm, addr)))
    return groups


def spatial_classes(groups):
    """{label: (passed, total)} for every class, plus the set that passed the test."""
    stats, trusted = {}, set()
    for label, members in groups.items():
        passed = [m for m in members if is_transform(m[2])]
        positions = {
            tuple(round(c, 1) for c in translation(m[2])) for m in passed
        } - {(0.0, 0.0, 0.0)}
        stats[label] = (len(passed), len(members))
        if (
            len(passed) >= MIN_SPATIAL_RATIO * len(members)
            and len(positions) >= MIN_DISTINCT_POSITIONS
        ):
            trusted.add(label)
    return stats, trusted


def collect(groups, wanted):
    """Rows [(addr, uuid_bytes, label, position)] for the classes we are reporting."""
    rows = []
    for label in wanted:
        for addr, raw, matrix in groups.get(label, ()):
            if is_transform(matrix):
                rows.append((addr, raw, label, translation(matrix)))
    return rows


def rank(rows, player, count=None):
    """Rows sorted by distance to the player, each prefixed with that distance."""
    px, py, pz = player
    rows = sorted(
        rows,
        key=lambda r: (r[3][0] - px) ** 2 + (r[3][1] - py) ** 2 + (r[3][2] - pz) ** 2,
    )
    if count is not None:
        rows = rows[:count]
    return [(math.dist(r[3], player), r) for r in rows]


def load_names(stream_path):
    """{uuid_bytes: name} from a level file - optional, purely cosmetic."""
    from madagascar.stream import load_stream

    lvl = load_stream(stream_path)
    names = {}
    for entity in lvl.entities():
        try:
            names[entity.entityID.bytes_le] = entity.tfbGetName()
        except Exception:
            pass
    return names


def describe(raw, names):
    import uuid as _uuid

    name = names.get(raw)
    return name if name else str(_uuid.UUID(bytes_le=raw))[:13]


def report(ranked, player, names, total):
    px, py, pz = player
    print(f"  player at ({px:.1f}, {py:.1f}, {pz:.1f})   "
          f"{total} entities with a position, showing {len(ranked)}")
    print(f"  {'dist':>9}  {'entity':<30} {'class':<14} "
          f"{'x':>9} {'y':>9} {'z':>9}  {'address':>10}")
    for dist, (addr, raw, label, (x, y, z)) in ranked:
        print(f"  {dist:9.2f}  {describe(raw, names)[:30]:<30} {label[:14]:<14} "
              f"{x:9.1f} {y:9.1f} {z:9.1f}  0x{addr:08x}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", "--count", type=int, default=20)
    ap.add_argument("--all-classes", action="store_true",
                    help="report every class that passes the transform test, "
                         "not just CProtoActor")
    ap.add_argument("--stream", help="optional level file, used only to show names")
    ap.add_argument("--watch", action="store_true",
                    help="refresh continuously until Ctrl+C")
    ap.add_argument("--interval", type=float, default=0.5)
    args = ap.parse_args()

    names = load_names(args.stream) if args.stream else {}
    if names:
        print(f"{args.stream}\n  {len(names)} names loaded")

    from madagascar.lib.game_memory import PlayerPosition

    pm = pymem.Pymem("Game.exe")
    base = pm.base_address
    head = base + (ENTITY_LIST_HEAD - IMAGE_BASE)
    player = PlayerPosition("Game.exe")

    nodes, _ = walk(pm, head)
    if not nodes:
        print("  !! could not walk the list - offsets are wrong or no level is loaded")
        return

    groups = group_by_class(pm, nodes, base)
    stats, trusted = spatial_classes(groups)
    print(f"  walked {len(nodes)} nodes; transform test at +0x{OFF_POS:x}:")
    for label, (passed, total) in sorted(stats.items(), key=lambda kv: -kv[1][1]):
        verdict = "spatial" if label in trusted else "no transform"
        print(f"    {passed:4d}/{total:<4d} {label:<16} {verdict}")

    wanted = sorted(trusted) if args.all_classes else \
        [c for c in DEFAULT_CLASSES if c in trusted]
    if not wanted:
        print("\n  !! nothing to report - "
              + ("no class passed the transform test"
                 if not trusted
                 else f"none of {', '.join(DEFAULT_CLASSES)} did; "
                      f"try --all-classes ({', '.join(sorted(trusted))})"))
        return
    print(f"\n  reporting: {', '.join(wanted)}\n")

    while True:
        rows = collect(groups, wanted)
        ranked = rank(rows, player.position, args.count)
        report(ranked, player.position, names, len(rows))
        if not args.watch:
            break
        time.sleep(args.interval)
        # re-walk: entities spawn and despawn while the level runs
        nodes, _ = walk(pm, head)
        groups = group_by_class(pm, nodes, base)
        print()


if __name__ == "__main__":
    main()
