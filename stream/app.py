"""Tkinter GUI that renders a RenderWare file as a browsable chunk tree."""

import sys
import tkinter as tk
from tkinter import ttk

import formats.lib.rw_basics as rw_basics
import formats.lib.rwConstants as rw_constants
import formats.lib.parser as parser

from .theme import COLORS, configure_style

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
    root = tk.Tk()
    root.title("RW Stream")
    root.geometry("900x500")
    root.configure(bg=COLORS["bg"])


    # --- ttk dark theme ---
    configure_style(root)


    # --- main horizontal split ---
    paned = ttk.PanedWindow(root, orient="horizontal")
    paned.pack(fill="both", expand=True)

    # --- left tree ---
    left = ttk.Frame(paned)

    # toolbar sits above the tree, inside the left pane
    toolbar = ttk.Frame(left)
    toolbar.pack(side="top", fill="x")

    tree_wrap = ttk.Frame(left)
    tree_wrap.pack(side="top", fill="both", expand=True)

    tree = ttk.Treeview(tree_wrap, show="tree", selectmode="browse")

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


    def on_close():
        root.destroy()

    with open(file_path, "rb") as f:
        file_parser = Parser(f.read(), endian="little")


    def reopen_file():
        tree.delete(*tree.get_children())
        with open(file_path, "rb") as f:
            file_parser = Parser(f.read(), endian="little")

    reopen_btn = ttk.Button(
        toolbar, text="⟳ Re-open", style="Toolbar.TButton", command=reopen_file
    )
    reopen_btn.pack(side="left", padx=4, pady=4)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
