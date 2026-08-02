"""Dark theme colours, ttk style setup, and tree icons for the analyzer GUI."""

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
import math

COLORS = {
    "bg": "#181818",
    "fg": "#d8dee9",
    "classname": "#61afef",  # blue types
    "kwarg": "#c678dd",  # purple fields
    "number": "#d19a66",  # orange numbers
    "string": "#98c379",  # green strings
    "constant": "#56b6c2",  # cyan constants
    "punct": "#5c6370",
    "operator": "#abb2bf",
    "comment": "#25f18b",
    "error": "#e06c75",
    "highlight": "#264f78",
    "panel_bg": "#1e1e1e",  # slightly lighter than tree bg
    "sel_bg": "#264f78",
    "sel_fg": "#ffffff",
    "tree_bg": "#181818",
    "header_bg": "#202020",
    "accent": "#61afef",
    "muted": "#8B9AA7",

    #--
    "enum_class": "#e04c6c",
    "enum_value": "#cece5d",

    #--
    "hex_read": "#d8dee9",
    "hex_not_read": "#6C727E",
    "hex_offset": "#8B9AA7",
    "hex_ascii": "#5D7080",
    "hex_ascii_read": "#8FB4CC",
}


def configure_style(root):
    """Apply the dark ``clam`` theme to ttk widgets. Requires a Tk root."""
    style = ttk.Style()
    style.theme_use("clam")

    #root.tk.call("tk", "scaling", 1.0)
    #if "tk::mac::ScrollFractions" in root.tk.call("info", "commands"):
    #    root.tk.call("tk::mac::ScrollFractions", True)

    style.configure("Treeview", rowheight=22)

    style.configure(
        "Treeview",
        background=COLORS["tree_bg"],
        foreground=COLORS["fg"],
        fieldbackground=COLORS["tree_bg"],
        borderwidth=0,
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["sel_bg"])],
        foreground=[("selected", COLORS["sel_fg"])],
    )

    # details tree sits on the lighter panel background
    style.configure(
        "Details.Treeview",
        background=COLORS["panel_bg"],
        fieldbackground=COLORS["panel_bg"],
    )

    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Treeview", relief="flat")
    style.layout(
        "Treeview", [("Treeview.treearea", {"sticky": "nswe"})]
    )  # drop the border box

    # paned window sashes
    style.configure("TPanedwindow", background=COLORS["bg"])
    style.configure(
        "Sash",
        sashthickness=4,
        gripcount=0,
        background=COLORS["punct"],
        bordercolor=COLORS["bg"],
        lightcolor=COLORS["bg"],
        darkcolor=COLORS["bg"],
    )

    # Flat scrollbar: drop the up/down arrow buttons, keep just trough + thumb.
    style.layout(
        "Vertical.TScrollbar",
        [
            (
                "Vertical.Scrollbar.trough",
                {
                    "sticky": "ns",
                    "children": [
                        ("Vertical.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})
                    ],
                },
            )
        ],
    )
    style.configure(
        "Vertical.TScrollbar",
        background="#4a4f5a",
        troughcolor=COLORS["panel_bg"],
        bordercolor=COLORS["panel_bg"],
        lightcolor="#4a4f5a",
        darkcolor="#4a4f5a",
        relief="flat",
        gripcount=0,
        width=12,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", "#6b7280"), ("pressed", "#7d8694")],
    )

    style.configure(
        "Toolbar.TButton",
        background=COLORS["panel_bg"],
        foreground=COLORS["fg"],
        bordercolor=COLORS["punct"],
        focuscolor=COLORS["bg"],
        relief="flat",
        padding=(10, 4),
    )
    style.map(
        "Toolbar.TButton",
        background=[("active", COLORS["sel_bg"]), ("pressed", COLORS["highlight"])],
        foreground=[("active", COLORS["sel_fg"])],
    )

    style.configure(
        "Toolbar.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["hex_not_read"],
    )

    style.configure(
        "Search.TEntry",
        fieldbackground=COLORS["panel_bg"],
        foreground=COLORS["fg"],
        insertcolor=COLORS["fg"],
        bordercolor=COLORS["punct"],
        lightcolor=COLORS["panel_bg"],
        darkcolor=COLORS["panel_bg"],
        relief="flat",
        padding=(6, 4),
    )
    style.map(
        "Search.TEntry",
        bordercolor=[("focus", COLORS["sel_bg"])],
        lightcolor=[("focus", COLORS["panel_bg"])],
        darkcolor=[("focus", COLORS["panel_bg"])],
    )

    base_font = tkfont.nametofont("TkDefaultFont")
    family = base_font.actual("family")
    base_size = abs(base_font.actual("size")) or 10
    title_font = (family, base_size + 2, "bold")
    small_font = (family, max(base_size - 2, 8))
    section_font = (family, max(base_size - 2, 8), "bold")
    strong_font = (family, base_size, "bold")

    # full-width header bar
    style.configure("Header.TFrame", background=COLORS["header_bg"])
    style.configure(
        "AppTitle.TLabel",
        background=COLORS["header_bg"],
        foreground=COLORS["fg"],
        font=title_font,
    )
    style.configure(
        "FileName.TLabel",
        background=COLORS["header_bg"],
        foreground=COLORS["muted"],
        font=small_font,
    )
    style.configure(
        "Header.TButton",
        background=COLORS["header_bg"],
        foreground=COLORS["fg"],
        bordercolor=COLORS["punct"],
        focuscolor=COLORS["header_bg"],
        relief="flat",
        padding=(10, 4),
    )
    style.map(
        "Header.TButton",
        background=[("active", COLORS["sel_bg"]), ("pressed", COLORS["highlight"])],
        foreground=[("active", COLORS["sel_fg"])],
    )

    # small uppercase captions above panes / sidebar fields
    style.configure(
        "Section.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["muted"],
        font=section_font,
    )

    # inspector header (selected chunk name)
    style.configure(
        "InspectorTitle.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
        font=strong_font,
    )
    style.configure(
        "InspectorHint.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["hex_not_read"],
        font=small_font,
    )

    # accent button for the contextual "teleport" action
    style.configure(
        "Accent.TButton",
        background=COLORS["panel_bg"],
        foreground=COLORS["accent"],
        bordercolor=COLORS["accent"],
        focuscolor=COLORS["panel_bg"],
        relief="flat",
        padding=(10, 4),
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLORS["sel_bg"]), ("pressed", COLORS["highlight"])],
        foreground=[("active", COLORS["sel_fg"])],
    )

    # bottom status bar
    style.configure("Status.TFrame", background=COLORS["header_bg"])
    style.configure(
        "Status.TLabel",
        background=COLORS["header_bg"],
        foreground=COLORS["muted"],
        font=small_font,
    )

    style.configure(
        "Filter.TCombobox",
        fieldbackground=COLORS["panel_bg"],
        background=COLORS["panel_bg"],
        foreground=COLORS["fg"],
        arrowcolor=COLORS["fg"],
        bordercolor=COLORS["punct"],
        lightcolor=COLORS["panel_bg"],
        darkcolor=COLORS["panel_bg"],
        relief="flat",
        padding=(6, 4),
    )
    style.map(
        "Filter.TCombobox",
        fieldbackground=[("readonly", COLORS["panel_bg"])],
        foreground=[("readonly", COLORS["fg"])],
        selectbackground=[("readonly", COLORS["panel_bg"])],
        selectforeground=[("readonly", COLORS["fg"])],
        bordercolor=[("focus", COLORS["sel_bg"])],
    )

    return style


def make_dot(color: str, size: int, padding_x: int) -> tk.PhotoImage:
    img = tk.PhotoImage(width=size + padding_x * 2, height=size)

    cx = size / 2
    cy = size / 2
    radius = size / 2 - 1

    # Light source (top-left)
    lx = cx - radius * 0.35
    ly = cy - radius * 0.35

    base = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))

    for x in range(size):
        for y in range(size):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= radius:
                # Edge shading
                edge = dist / radius

                # Highlight from light source
                light_dist = math.sqrt((x - lx) ** 2 + (y - ly) ** 2) / radius
                highlight = max(0, 1 - light_dist) ** 2

                # Bottom-right inset shadow
                shadow = max(0, (dx + dy) / (radius * 2))

                factor = (
                    0.75
                    + highlight * 0.45
                    - edge * 0.20
                    - shadow * 0.25
                )

                factor = max(0.0, min(1.3, factor))

                rgb = tuple(
                    min(255, max(0, int(c * factor)))
                    for c in base
                )

                img.put(
                    "#%02X%02X%02X" % rgb,
                    (x + padding_x, y)
                )

    return img


def make_icons(size=15, padding_x=5):
    """Build the green/blue/gray 3D dot icons used in the tree."""
    return (
        make_dot("#00D100", size, padding_x),
        make_dot("#1D9BF2", size, padding_x),
        make_dot("#9C9C9C", size, padding_x),
        make_dot("#FFEE00", size, padding_x),
    )
