"""Walk Game.exe's live entity list and report which entities actually exist.

Answers the one question black-box testing cannot: was a cloned entity created
at all, or created and simply not drawn?

The list was located by RE: head at 0x0062fea8 (image base 0x400000), nodes
carry their 16-byte instance uuid at +0x08 and the next pointer at +0x18.
Those offsets are ASSUMPTIONS - the script validates them by checking how many
uuids from the .stream file it finds, and refuses to trust a bad walk.

    python -m madkit.tools.livescan [path-to-stream]
"""

import sys
from typing import Protocol, cast

import pymem
from pymem.exception import MemoryReadError

IMAGE_BASE = 0x400000
ENTITY_LIST_HEAD = 0x0062FEA8
OFF_UUID = 0x08
OFF_NEXT = 0x18
MAX_NODES = 100_000


class ProcessMemory(Protocol):
    """The slice of ``pymem.Pymem`` that ``walk`` needs (pymem ships no types)."""

    def read_uint(self, address: int) -> int: ...
    def read_bytes(self, address: int, length: int) -> bytes: ...


def walk(
    pm: ProcessMemory,
    head_addr: int,
) -> tuple[list[tuple[int, bytes]], bool | None]:
    """Return ([(node_addr, uuid_bytes)], deref). Tries head as a pointer, then as a node."""
    for deref in (True, False):
        nodes: list[tuple[int, bytes]] = []
        seen: set[int] = set()
        addr = head_addr
        if deref:
            try:
                addr = pm.read_uint(head_addr)
            except MemoryReadError:
                addr = (
                    0  # head is not a readable pointer: skip to treating it as a node
                )
        while addr and addr not in seen and len(nodes) < MAX_NODES:
            seen.add(addr)
            try:
                raw = pm.read_bytes(addr + OFF_UUID, 16)
                nxt = pm.read_uint(addr + OFF_NEXT)
            except MemoryReadError:
                break
            nodes.append((addr, raw))
            addr = nxt
        if len(nodes) > 1:
            return nodes, deref
    return [], None


def main():
    stream_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "C:/Users/maxst/Desktop/Madagascar/Game/Levels/banquet.stream"
    )

    from madformats.stream import load_stream

    lvl = load_stream(stream_path)
    file_ents = {e.entityID.bytes_le: e for e in lvl.entities()}
    print(f"{stream_path}\n  {len(file_ents)} entities in the file")

    pm = pymem.Pymem("Game.exe")
    base = pm.base_address
    head = base + (ENTITY_LIST_HEAD - IMAGE_BASE)
    print(f"  Game.exe base 0x{base:08x}, list head 0x{head:08x}")

    # pymem's inferred return types include raw ctypes; at runtime they are int/bytes
    nodes, deref = walk(cast("ProcessMemory", pm), head)
    if not nodes:
        print("  !! could not walk the list - offsets are wrong or no level is loaded")
        return

    live = {raw for _, raw in nodes}
    hit = live & set(file_ents)
    print(
        f"  walked {len(nodes)} nodes (head {'is a pointer' if deref else 'is the node'})"
    )
    print(f"  {len(hit)} of them match a uuid from the file")

    if len(hit) < len(file_ents) * 0.5:
        print(
            "  !! fewer than half matched - do NOT trust these offsets; "
            "the walk is landing on the wrong structure"
        )
        return

    missing = [e for raw, e in file_ents.items() if raw not in live]
    print(f"\n  {len(file_ents) - len(missing)} created, {len(missing)} NOT created")

    clones = [
        e for e in file_ents.values() if (e.tfbGetName() or "").startswith("MODDED")
    ]
    if clones:
        print("\n  clones:")
        for e in sorted(clones, key=lambda e: e.tfbGetName() or ""):
            state = "LIVE " if e.entityID.bytes_le in live else "ABSENT"
            print(f"    {state}  {e.tfbGetName() or '':<14} {e.entityID}")

    if missing:
        by_behaviour: dict[str, int] = {}
        for e in missing:
            by_behaviour[e.behaviour] = by_behaviour.get(e.behaviour, 0) + 1
        print("\n  missing entities by behaviour:")
        for b, n in sorted(by_behaviour.items(), key=lambda kv: -kv[1]):
            print(f"    {n:5d}  {b}")


if __name__ == "__main__":
    main()
