"""Live window listing the entities closest to the player, refreshed every 500 ms.

The GUI front-end for tools/nearest.py: same walk of Game.exe's entity list, same
transform test that decides which classes actually keep a world matrix at +0x148,
just repainted on a timer instead of printed once. Needs no .stream file - by
default it reports CProtoActor, the class every placed gameplay object uses.

Entity names do not exist in memory (the loader discards them), so rows are keyed
by uuid. Pass a level file, or use the Names... button, to attach names to those
uuids purely for readability.

    python tools/nearest_gui.py [path-to-stream]
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk

import pymem

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from livescan import IMAGE_BASE, ENTITY_LIST_HEAD, walk  # noqa: E402
from nearest import (  # noqa: E402
    DEFAULT_CLASSES,
    OFF_POS,
    collect,
    describe,
    group_by_class,
    load_names,
    rank,
    spatial_classes,
)

UPDATE_MS = 500

COLUMNS = (
    ("dist", 80, "e"),
    ("entity", 220, "w"),
    ("class", 105, "w"),
    ("x", 75, "e"),
    ("y", 75, "e"),
    ("z", 75, "e"),
    ("address", 90, "e"),
)


class NearestViewer:
    def __init__(self, stream_path=None):
        self.pm = None
        self.base = 0
        self.head = 0
        self.player = None
        self.groups = {}
        self.trusted = set()
        self.ranked = []
        self.items = []
        self.names = {}
        self.last_count = 20

        self.root = tk.Tk()
        self.root.title("Nearest Entities")
        self.root.geometry("800x520")
        self.root.minsize(640, 360)

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        self.player_label = ttk.Label(
            main,
            text="player at ?",
            font=("Consolas", 11),
        )
        self.player_label.pack(anchor="w")

        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=(8, 6))

        ttk.Label(controls, text="show").pack(side="left")

        self.count = tk.IntVar(value=20)
        ttk.Spinbox(
            controls,
            from_=1,
            to=500,
            width=5,
            textvariable=self.count,
        ).pack(side="left", padx=(6, 12))

        self.all_classes = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            controls,
            text="all spatial classes",
            variable=self.all_classes,
        ).pack(side="left")

        ttk.Button(
            controls,
            text="Reload",
            command=self.reattach,
        ).pack(side="right")

        ttk.Button(
            controls,
            text="Copy",
            command=self.copy_list,
        ).pack(side="right", padx=(0, 6))

        ttk.Button(
            controls,
            text="Names...",
            command=self.pick_names,
        ).pack(side="right", padx=(0, 6))

        tree_frame = ttk.Frame(main)
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=[c[0] for c in COLUMNS],
            show="headings",
            selectmode="browse",
        )
        for key, width, anchor in COLUMNS:
            self.tree.heading(key, text=key)
            self.tree.column(key, width=width, anchor=anchor, stretch=(key == "entity"))

        scroll = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.status = ttk.Label(
            main,
            text="",
            font=("Consolas", 9),
            foreground="#606060",
            wraplength=760,
            justify="left",
        )
        self.status.pack(anchor="w", pady=(6, 0))

        if stream_path:
            self.load_names_from(stream_path)

        self.reattach()
        self.update_list()

        self.root.mainloop()

    def reattach(self):
        """(Re)open the process and re-run the transform test on every class."""
        from madagascar.lib.game_memory import PlayerPosition

        try:
            self.pm = pymem.Pymem("Game.exe")
            self.player = PlayerPosition("Game.exe")
            self.base = self.pm.base_address
            self.head = self.base + (ENTITY_LIST_HEAD - IMAGE_BASE)

            nodes, _ = walk(self.pm, self.head)
            if not nodes:
                raise RuntimeError("could not walk the entity list - no level loaded?")

            self.groups = group_by_class(self.pm, nodes, self.base)
            stats, self.trusted = spatial_classes(self.groups)
            if not self.trusted:
                raise RuntimeError(
                    f"no class passed the transform test at +0x{OFF_POS:x}"
                )

            spatial = " ".join(
                f"{label} {stats[label][0]}/{stats[label][1]}"
                for label in sorted(self.trusted)
            )
            self.set_status(
                f"{len(nodes)} nodes in {len(self.groups)} classes  |  "
                f"+0x{OFF_POS:x} transform test passed by: {spatial}"
                + (f"  |  {len(self.names)} names loaded" if self.names else "")
            )
        except Exception as e:  # noqa: BLE001
            self.pm = None
            self.set_status(f"not attached: {e}", error=True)

    def pick_names(self):
        path = filedialog.askopenfilename(
            title="Level file (names only)",
            filetypes=[("Stream files", "*.stream"), ("All files", "*.*")],
        )
        if path:
            self.load_names_from(path)

    def load_names_from(self, path):
        try:
            self.names = load_names(path)
            self.set_status(f"{len(self.names)} names loaded from {path}")
        except Exception as e:  # noqa: BLE001
            self.names = {}
            self.set_status(f"could not read {path}: {e}", error=True)

    def set_status(self, text, error=False):
        self.status.config(
            text=text,
            foreground="#b00000" if error else "#606060",
        )

    def wanted_classes(self):
        if self.all_classes.get():
            return sorted(self.trusted)
        return [c for c in DEFAULT_CLASSES if c in self.trusted]

    def row_count(self):
        """Spinbox value, ignoring the half-typed states an editable box goes through."""
        try:
            self.last_count = max(1, self.count.get())
        except tk.TclError:
            pass
        return self.last_count

    def update_list(self):
        try:
            if self.pm is None:
                raise RuntimeError("not attached - press Reload")

            # re-walk every tick: entities spawn and despawn while the level runs
            nodes, _ = walk(self.pm, self.head)
            self.groups = group_by_class(self.pm, nodes, self.base)

            wanted = self.wanted_classes()
            if not wanted:
                raise RuntimeError(
                    f"{', '.join(DEFAULT_CLASSES)} not present - "
                    "tick 'all spatial classes'"
                )

            player = self.player.position
            rows = collect(self.groups, wanted)
            self.ranked = rank(rows, player, self.row_count())

            self.player_label.config(
                text=f"player at ({player[0]:9.2f}, {player[1]:9.2f}, {player[2]:9.2f})"
                f"   {len(rows)} {'/'.join(wanted)} entities"
            )
            self.fill(self.ranked)

        except Exception as e:  # noqa: BLE001
            self.player_label.config(text="player at ?")
            self.set_status(str(e), error=True)

        self.root.after(UPDATE_MS, self.update_list)

    def fill(self, ranked):
        """Rewrite rows in place so scroll position and selection survive a tick."""
        while len(self.items) < len(ranked):
            self.items.append(self.tree.insert("", "end", values=()))

        for item in self.items[len(ranked):]:
            self.tree.delete(item)
        del self.items[len(ranked):]

        for item, (dist, row) in zip(self.items, ranked):
            addr, raw, label, pos = row
            self.tree.item(
                item,
                values=(
                    f"{dist:.2f}",
                    describe(raw, self.names),
                    label,
                    f"{pos[0]:.1f}",
                    f"{pos[1]:.1f}",
                    f"{pos[2]:.1f}",
                    f"0x{addr:08x}",
                ),
            )

    def copy_list(self):
        lines = []
        for dist, (addr, raw, label, pos) in self.ranked:
            lines.append(
                f"{dist:9.2f}  {describe(raw, self.names):<30} {label:<14} "
                f"{pos[0]:9.1f} {pos[1]:9.1f} {pos[2]:9.1f}  0x{addr:08x}"
            )

        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.root.update()


if __name__ == "__main__":
    NearestViewer(sys.argv[1] if len(sys.argv) > 1 else None)
