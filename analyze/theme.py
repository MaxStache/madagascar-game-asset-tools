"""Dark theme colours, ttk style setup, and tree icons for the analyzer GUI."""

import tkinter as tk
from tkinter import ttk

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

    #--
    "enum_class": "#e04c6c",
    "enum_value": "#cece5d",

    #--
    "hex_read": "#d8dee9",
    "hex_not_read": "#6C727E",
    "hex_offset": "#8B9AA7",
    "hex_ascii": "#5D7080",
}


def configure_style():
    """Apply the dark ``clam`` theme to ttk widgets. Requires a Tk root."""
    style = ttk.Style()
    style.theme_use("clam")

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

    return style


def make_icons(size=15, padding_x=5):
    """Build the green/blue/gray dot icons used in the tree. Requires a Tk root."""
    green_dot = tk.PhotoImage(width=size + padding_x * 2, height=size)
    blue_dot = tk.PhotoImage(width=size + padding_x * 2, height=size)
    gray_dot = tk.PhotoImage(width=size + padding_x * 2, height=size)

    for x in range(size):
        for y in range(size):
            if (x - size // 2) ** 2 + (y - size // 2) ** 2 <= (size // 2 - 1) ** 2:
                green_dot.put("#00D100", (x + padding_x, y))
                blue_dot.put("#1D9BF2", (x + padding_x, y))
                gray_dot.put("#9C9C9C", (x + padding_x, y))

    return green_dot, blue_dot, gray_dot
