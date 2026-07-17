"""Tkinter GUI that renders a RenderWare file as a browsable chunk tree."""

import sys
import tkinter as tk
from tkinter import ttk
import traceback

from formats.streamfuncs import RW_sf_CreateEntity

from .formatting import pretty_object
from formats.lib.rw_basics import RW_Matrix4x4
import formats.lib.rwConstants as rw_constants
from formats.lib.rwConstants import strfunc_func
import formats.lib.parser as parser
from formats.lib.game_memory import PlayerPosition

from tkinter.messagebox import showerror

import formats.stream as stream
from stream.syntax import configure_tags, highlight

from .theme import COLORS, configure_style, make_icons

import ctypes as ct

RWSectionType = rw_constants.RWSectionType
Parser = parser.Parser

STR_FUNCS = {}
SELECTED = None

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
    set_window_attribute(hwnd, rendering_policy, ct.byref(value), ct.sizeof(value))


def run(file_path):
    """Open ``file_path`` and launch the window."""
    root = tk.Tk()
    root.title("RW Stream")
    root.geometry("900x500")
    root.configure(bg=COLORS["bg"])

    dot_green, dot_blue, dot_gray, dot_yellow = make_icons()

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

    TREE_ORDER = []
    SEARCH_TEXT = {}

    def apply_filter(*_args):
        query = search_var.get().strip().lower()
        for iid in TREE_ORDER:
            if not query or query in SEARCH_TEXT.get(iid, ""):
                tree.reattach(iid, "", "end")
            else:
                tree.detach(iid)

    search_var = tk.StringVar()
    search_var.trace_add("write", apply_filter)

    ttk.Label(toolbar, text="Search:", style="Toolbar.TLabel").pack(
        side="left", padx=(6, 0), pady=4
    )
    search_entry = ttk.Entry(toolbar, textvariable=search_var, style="Search.TEntry")
    search_entry.pack(side="left", fill="x", expand=True, padx=6, pady=4)

    tree_wrap = ttk.Frame(left)
    tree_wrap.pack(side="top", fill="both", expand=True)

    tree = ttk.Treeview(tree_wrap, show="tree", selectmode="browse")

    vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)

    tree.configure(yscrollcommand=vsb.set)

    vsb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)

    paned.add(left, weight=2)

    # --- right vertical split ---
    right = ttk.PanedWindow(paned, orient="vertical")

    # --- top: hex view ---
    hex_frame = ttk.Frame(right)

    details_tree_wrap = ttk.Frame(hex_frame)
    details_tree_wrap.pack(side="top", fill="both", expand=True)

    details_tree = ttk.Treeview(
        details_tree_wrap, show="tree", selectmode="browse", style="Details.Treeview"
    )
    hvsb = ttk.Scrollbar(
        details_tree_wrap, orient="vertical", command=details_tree.yview
    )

    details_tree.configure(yscrollcommand=hvsb.set)

    hvsb.pack(side="right", fill="y")
    details_tree.pack(side="left", fill="both", expand=True)

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

    right.add(hex_frame, weight=1)
    right.add(details_frame, weight=1)

    paned.add(right, weight=1)

    # set initial sizes
    root.update()

    set_dark_titlebar(root)

    paned.sashpos(0, 500)
    right.sashpos(0, 250)

    def tp_to_selected_entity():
        if SELECTED is None:
            return

        sf = STR_FUNCS[SELECTED]

        if not isinstance(sf, RW_sf_CreateEntity):
            return

        entity_matrix_class = sf.find_first_class_with_command("CSystemCommands", 1)
        if not entity_matrix_class or entity_matrix_class is None:
            showerror("Error", "Selected entity has no valid matrix (position).")
            return
        
        entity_matrix_data = entity_matrix_class.find_first_attribute(1).data

        entity_matrix_parser = Parser(entity_matrix_data, endian="little")
        entity_matrix = RW_Matrix4x4.read(entity_matrix_parser)

        entity_translation = entity_matrix.get_translation()

        print(f"Teleporting to position: {entity_translation}")

        try:
            pos = PlayerPosition()
            pos.set_position(entity_translation.x, entity_translation.y, entity_translation.z)
        except Exception as e:
            print(f"Error teleporting: {e}")
            traceback.print_exc()
            showerror("Could not teleport", "Teleport to entity failed, is game open, are you in a level and no cutscene playing?")


    # TOOLBAR
    tp_to_entity = ttk.Button(
        toolbar, text="Teleport to selected", style="Toolbar.TButton", command=tp_to_selected_entity
    )
    # ---

    def on_close():
        root.destroy()

    def populate(strm: stream.RW_StreamFile):
        TREE_ORDER.clear()
        SEARCH_TEXT.clear()

        SF_TO_COLOR = {
            strfunc_func.sf_CreateEntity: dot_green,
            strfunc_func.sf_LoadEmbeddedAsset: dot_blue,
            strfunc_func.sf_PlacementNew: dot_yellow,
        }

        for sf in strm.contents:
            color = SF_TO_COLOR.get(sf.streamfunc, dot_gray)
            label = ""
            name = ""
            behaviour = ""
            if sf.streamfunc == strfunc_func.sf_CreateEntity:
                ctfbcommand = sf.find_first_class_with_command("CTFBCommand", 0)
                name = (
                    ctfbcommand.find_first_attribute(0)
                    .data.split(b"\00")[0]
                    .decode("latin-1")
                    if ctfbcommand
                    else "Unnamed"
                )
                label = f" - {name}"
                behaviour = sf.behaviour or ""

            if sf.streamfunc == strfunc_func.sf_LoadEmbeddedAsset:
                name = sf.name
                label = f" - {name}"

            iid = tree.insert(
                "",
                "end",
                text=sf.streamfunc.name + label,
                values=(sf.header.type, sf.header.size),
                image=color,
            )

            STR_FUNCS[iid] = sf
            TREE_ORDER.append(iid)
            SEARCH_TEXT[iid] = f"{sf.streamfunc.name} {name} {behaviour}".lower()

    with open(file_path, "rb") as f:
        strm = stream.load_stream(file_path)

        populate(strm)

    def on_select(event):
        global SELECTED

        sel = tree.selection()

        if not sel:
            return

        iid = sel[0]
        SELECTED = iid

        sf = STR_FUNCS[iid]

        pretty = pretty_object(sf)

        details_label.config(state="normal")
        details_label.delete("1.0", "end")  # remove existing content

        tp_to_entity.pack_forget()
        if isinstance(sf, RW_sf_CreateEntity):
            tp_to_entity.pack(side="left", padx=4, pady=4)

            details_tree.delete(*details_tree.get_children())  # clear details tree

            details_tree.insert("", "end", text=f"Behaviour: {sf.behaviour}", open=True)
            details_tree.insert("", "end", text=f"Entity ID: {{{sf.entityID}}}", open=True)
            details_tree.insert("", "end", text=f"Is Global: {sf.isGlobal}", open=True)
            for cls in sf.classes:
                cls_iid = details_tree.insert(
                    "", "end", text=f"Class: {cls.class_name}", open=True
                )
                for attr in cls.attributes:
                    details_tree.insert(
                        cls_iid,
                        "end",
                        text=f"CMD: {attr.command}, Data Size: {len(attr.data)} bytes",
                    )

        highlight(details_label, pretty)  # inserts `pretty` and applies tags

        details_label.config(state="disabled")

    tree.bind("<<TreeviewSelect>>", on_select)

    def reopen_file():
        global SELECTED

        tree.delete(*tree.get_children())
        STR_FUNCS.clear()
        tp_to_entity.pack_forget()
        strm = stream.load_stream(file_path)

        populate(strm)
        apply_filter()
        on_select(None)
        SELECTED = None

    reopen_btn = ttk.Button(
        toolbar, text="⟳ Re-open", style="Toolbar.TButton", command=reopen_file
    )
    reopen_btn.pack(side="left", padx=4, pady=4)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
