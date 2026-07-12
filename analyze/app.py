"""Tkinter GUI that renders a RenderWare file as a browsable chunk tree."""

import importlib
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import ttk

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from formats import sections
import formats.lib.rw_basics as rw_basics
import formats.lib.rwConstants as rw_constants
import formats.lib.parser as parser

from .formatting import hexdump, pretty_object
from .rwtree import read_recursive
from .syntax import configure_tags, highlight
from .theme import COLORS, configure_style, make_icons

import ctypes as ct

RWHeader = rw_basics.RWHeader
RWSectionType = rw_constants.RWSectionType
Parser = parser.Parser

def set_dark_titlebar(window):
    if sys.platform != "win32":
        return
    """
    MORE INFO:
    https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute
    """
    window.update()
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    set_window_attribute = ct.windll.dwmapi.DwmSetWindowAttribute
    get_parent = ct.windll.user32.GetParent
    hwnd = get_parent(window.winfo_id())
    rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
    value = 2
    value = ct.c_int(value)
    set_window_attribute(hwnd, rendering_policy, ct.byref(value),
                         ct.sizeof(value))

def run(file_path):
    """Open ``file_path`` and launch the analyzer window."""
    leaf_bytes = {}
    tree_headers = {}

    root = tk.Tk()
    root.title("RW Tree")
    root.geometry("900x500")
    root.configure(bg=COLORS["bg"])


    # --- ttk dark theme ---
    configure_style(root)

    # --- icons ---
    green_dot, blue_dot, gray_dot = make_icons()

    def populate(tree, parent, node):
        header, data, children = node

        try:
            sect = RWSectionType(header.type).name
        except ValueError:
            sect = "Unknown"
        label = f"{sect}  (0x{header.type:X}, {header.size} B)"

        color = blue_dot if children else green_dot
        is_implemented = (
            sections.SECTION_REGISTRY.get(header.type)
            not in [sections.RW_Section_NotImplemented, None]
        ) or header.type == RWSectionType.rwID_STRUCT.value

        iid = tree.insert(
            parent,
            "end",
            text=label,
            image=color if is_implemented else gray_dot,
            open=True,
        )

        leaf_bytes[iid] = data
        tree_headers[iid] = header

        if not parent:
            tree.selection_set(iid)

        for child in children:
            populate(tree, iid, child)

    def reload_sections():
        """Hot-reload the section parsers and re-render the current selection.

        Submodules are reloaded before the package so that re-executing
        ``formats/sections/__init__.py`` rebuilds SECTION_REGISTRY from the
        freshly-defined classes.
        """
        global sections

        try:
            submods = [
                name for name in sys.modules if name.startswith("formats.sections.")
            ]
            for name in submods:
                importlib.reload(sys.modules[name])

            sections = importlib.reload(sys.modules["formats.sections"])
            importlib.reload(sys.modules["formats.lib.rw_basics"])
            importlib.reload(sys.modules["formats.lib.rwConstants"])
            importlib.reload(sys.modules["formats.lib.parser"])

        except Exception as e:
            print(f"\033[31;1;4mFailed to reload sections: {e}\033[0m")
            return

        # Refresh the details/hex view for whatever is currently selected.
        on_select(None)

        print("Reloaded section parsers and refreshed view.")

    # --- main horizontal split ---
    paned = ttk.PanedWindow(root, orient="horizontal")
    paned.pack(fill="both", expand=True)

    # --- left tree ---
    left = ttk.Frame(paned)

    # toolbar sits above the tree, inside the left pane
    toolbar = ttk.Frame(left)
    toolbar.pack(side="top", fill="x")

    reload_btn = ttk.Button(
        toolbar,
        text="⟳ Reload sections/ (DEBUG)",
        style="Toolbar.TButton",
        command=reload_sections,
    )
    reload_btn.pack(side="left", padx=4, pady=4)

    tree_wrap = ttk.Frame(left)
    tree_wrap.pack(side="top", fill="both", expand=True)

    tree = ttk.Treeview(tree_wrap, show="tree")

    vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)

    tree.configure(yscrollcommand=vsb.set)

    vsb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)

    paned.add(left, weight=1)

    # --- right vertical split ---
    right = ttk.PanedWindow(paned, orient="vertical")

    # --- top: hex view ---
    hex_frame = ttk.Frame(right)

    hexview = tk.Text(
        hex_frame,
        wrap="none",
        font="TkFixedFont",
        state="disabled",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
        insertbackground=COLORS["fg"],
        selectbackground=COLORS["sel_bg"],
        selectforeground=COLORS["sel_fg"],
        borderwidth=0,
        highlightthickness=0,
    )
    hexview.configure(
        bg=COLORS["panel_bg"], fg=COLORS["fg"], insertbackground=COLORS["fg"]
    )

    hvsb = ttk.Scrollbar(hex_frame, orient="vertical", command=hexview.yview)

    hexview.configure(yscrollcommand=hvsb.set)

    hvsb.pack(side="right", fill="y")
    hexview.pack(side="left", fill="both", expand=True)

    # --- bottom: details panel ---
    details_frame = ttk.Frame(right)

    details_label = tk.Text(
        details_frame,
        font=("Cascadia Code", 10, "normal"),
        state="disabled",
        background=COLORS["panel_bg"],
        foreground=COLORS["fg"],
        insertbackground=COLORS["fg"],
        selectbackground=COLORS["sel_bg"],
        selectforeground=COLORS["sel_fg"],
        borderwidth=0,
        highlightthickness=0,
    )

    configure_tags(details_label)  # one-time tag color setup

    dlsb = ttk.Scrollbar(details_frame, orient="vertical", command=details_label.yview)

    details_label.configure(yscrollcommand=dlsb.set)

    dlsb.pack(side="right", fill="y")
    details_label.pack(side="left", fill="both", expand=True)

    right.add(hex_frame, weight=3)
    right.add(details_frame, weight=1)

    paned.add(right, weight=1)

    # set initial sizes
    root.update()

    set_dark_titlebar(root)

    paned.sashpos(0, 400)
    right.sashpos(0, 100)

    def read_section(iid):
        root.title("RW Tree - parsing....")
        """Parse the section at `iid`, passing its parsed parent section (if any)."""
        header = tree_headers[iid]
        section = sections.SECTION_REGISTRY.get(header.type)

        if not section:
            raise ValueError(
                f"No section parser registered for type {header.type} (0x{header.type:X})"
            )
        # Skip past any Extension parent to the chunk it is attached to, so a
        # section sees its real parent (e.g. a Geometry) rather than the Extension.
        parent_iid = tree.parent(iid)
        while (
            parent_iid
            and tree_headers[parent_iid].type == RWSectionType.rwID_EXTENSION.value
        ):
            parent_iid = tree.parent(parent_iid)

        parent_section, parent_read_end = (
            read_section(parent_iid) if parent_iid else (None, None)
        )

        # A STRUCT (0x1) has no standalone parser — the owning section parses it
        # into `.struct`. Show that parsed struct rather than the raw fallback.
        if header.type == RWSectionType.rwID_STRUCT.value:
            struct = getattr(parent_section, "struct", None)
            if struct is not None:
                return struct, parent_read_end

        sec_parser = Parser(header.pack() + leaf_bytes[iid], endian="little")
        parsed = section.read(
            sec_parser,
            parent=parent_section,
        )

        root.title("RW Tree")
        return parsed, sec_parser.offset

    def on_select(event):
        sel = tree.selection()

        if not sel:
            return

        iid = sel[0]

        end_offset = 0
        abc = None

        try:
            abc, end_offset = read_section(iid)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)

            print("\nTRACEBACK:")
            for i, t in enumerate(tb):
                print(f"    {i}: {t.filename}:{t.lineno}")

            details_label.config(state="normal")
            details_label.delete("1.0", "end")
            details_label.insert("1.0", f"Failed to parse section: {e}")
            print(f"\033[31;1;4mFailed to parse section: {e}\033[0m")
            details_label.config(state="disabled")
            hexview.config(state="disabled")

        hexview.config(state="normal")
        hexview.delete("1.0", "end")

        if iid in leaf_bytes:
            hexdump(hexview, leaf_bytes[iid], parse_end=end_offset-12) # - 12 for the header size
        
        root.title("RW Tree - preparing....")

        if abc is None:
            pretty = "# No parser registered for this section type."
        else:
            pretty = pretty_object(abc)

        details_label.config(state="normal")
        details_label.delete("1.0", "end")  # remove existing content

        highlight(details_label, pretty)  # inserts `pretty` and applies tags

        details_label.config(state="disabled")

        root.title("RW Tree")

        hexview.config(state="disabled")

    tree.bind("<<TreeviewSelect>>", on_select)

    last_reload = 0.0
    RELOAD_COOLDOWN = 1.0  # seconds

    def on_file_changed(path: Path):
        nonlocal last_reload

        now = time.monotonic()
        if now - last_reload < RELOAD_COOLDOWN:
            return

        last_reload = now

        print(f"File changed: {path}")
        reload_sections()

    class WatchHandler(FileSystemEventHandler):
        def on_modified(self, event):
            if not event.is_directory:
                # watchdog fires this on its own thread; Tkinter is not
                # thread-safe, so bounce the work onto the Tk main loop.
                root.after(0, on_file_changed, Path(event.src_path))

    directory = Path("./formats/sections")

    observer = Observer()
    observer.schedule(WatchHandler(), str(directory), recursive=True)
    observer.start()

    def on_close():
        observer.stop()
        observer.join()
        root.destroy()

    with open(file_path, "rb") as f:
        file_parser = Parser(f.read(), endian="little")

        populate(tree, "", read_recursive(file_parser))

    def reopen_file():
        tree.delete(*tree.get_children())
        leaf_bytes.clear()
        tree_headers.clear()
        with open(file_path, "rb") as f:
            file_parser = Parser(f.read(), endian="little")

            populate(tree, "", read_recursive(file_parser))

    reopen_btn = ttk.Button(
        toolbar, text="⟳ Re-open", style="Toolbar.TButton", command=reopen_file
    )
    reopen_btn.pack(side="left", padx=4, pady=4)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
