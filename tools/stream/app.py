"""Tkinter GUI that renders a RenderWare file as a browsable chunk tree."""

import os
import sys
import uuid
import tkinter as tk
from tkinter import ttk
import traceback

from madagascar.streamfuncs import (
    RW_sf_CreateEntity,
    RW_sf_LoadEmbeddedAsset,
    RW_sf_PlacementNew,
)

from madagascar.lib.rw_basics import RW_Matrix4x4, RW_StreamFunc_NotImplemented
import madagascar.lib.rwConstants as rw_constants
from madagascar.lib.rwConstants import strfunc_func
import madagascar.lib.parser as parser
from madagascar.lib.game_memory import PlayerPosition

from tkinter.messagebox import showerror

import madagascar.stream as stream
from madagascar.streamfuncs.stringfuncs.sf_SetDirectorsCameraMatrix import RW_sf_SetDirectorsCameraMatrix
from tools.stream.syntax import configure_tags

from .theme import COLORS, configure_style, make_icons

import ctypes as ct

RWSectionType = rw_constants.RWSectionType
Parser = parser.Parser

from madagascar.lib.entityAttributeDocs import CREATE_ENTITY_ATTRIBUTE_COMMANDS
from madagascar.lib.entityAtributeDocs.CProtoActor import parse_CProtoActor_attribute1

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
    root.geometry("1200x720")
    root.minsize(900, 500)
    root.configure(bg=COLORS["bg"])

    dot_green, dot_blue, dot_gray, dot_yellow = make_icons()

    # --- ttk dark theme ---
    configure_style(root)

    # --- app shell: header / body / status bar ---
    root.rowconfigure(1, weight=1)
    root.columnconfigure(0, weight=1)

    header = ttk.Frame(root, style="Header.TFrame", padding=(12, 8))
    header.grid(row=0, column=0, sticky="ew")

    ttk.Label(header, text="RW Stream", style="AppTitle.TLabel").pack(side="left")
    ttk.Label(
        header, text=os.path.basename(file_path), style="FileName.TLabel"
    ).pack(side="left", padx=(10, 0))

    # --- main horizontal split ---
    paned = ttk.PanedWindow(root, orient="horizontal")
    paned.grid(row=1, column=0, sticky="nsew")

    status = ttk.Frame(root, style="Status.TFrame", padding=(12, 4))
    status.grid(row=2, column=0, sticky="ew")

    status_path = ttk.Label(status, text=file_path, style="Status.TLabel")
    status_path.pack(side="left")
    status_count = ttk.Label(status, text="", style="Status.TLabel")
    status_count.pack(side="right")

    # --- left sidebar: search / filter / chunk tree ---
    left = ttk.Frame(paned, padding=(10, 8, 6, 8))
    left.columnconfigure(0, weight=1)
    left.rowconfigure(5, weight=1)

    TREE_ORDER = []
    SEARCH_TEXT = {}
    ITEM_BEHAVIOUR = {}

    def apply_filter(*_args):
        query = search_var.get().strip().lower()
        behaviour = behaviour_var.get()
        shown = 0
        for iid in TREE_ORDER:
            matches_search = not query or query in SEARCH_TEXT.get(iid, "")
            matches_behaviour = (
                behaviour == "All" or ITEM_BEHAVIOUR.get(iid) == behaviour
            )
            if matches_search and matches_behaviour:
                tree.reattach(iid, "", "end")
                shown += 1
            else:
                tree.detach(iid)
        total = len(TREE_ORDER)
        if shown == total:
            status_count.config(text=f"{total} chunks")
        else:
            status_count.config(text=f"{shown} of {total} chunks")

    search_var = tk.StringVar()
    search_var.trace_add("write", apply_filter)

    behaviour_var = tk.StringVar(value="All")
    behaviour_var.trace_add("write", apply_filter)

    ttk.Label(left, text="SEARCH", style="Section.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    search_entry = ttk.Entry(left, textvariable=search_var, style="Search.TEntry")
    search_entry.grid(row=1, column=0, sticky="ew", pady=(2, 8))

    ttk.Label(left, text="BEHAVIOUR", style="Section.TLabel").grid(
        row=2, column=0, sticky="w"
    )
    behaviour_combo = ttk.Combobox(
        left,
        textvariable=behaviour_var,
        state="readonly",
        style="Filter.TCombobox",
        values=("All",),
    )
    behaviour_combo.grid(row=3, column=0, sticky="ew", pady=(2, 8))
    behaviour_combo.bind(
        "<<ComboboxSelected>>", lambda _e: behaviour_combo.selection_clear()
    )

    ttk.Label(left, text="CHUNKS", style="Section.TLabel").grid(
        row=4, column=0, sticky="w", pady=(0, 2)
    )

    tree_wrap = ttk.Frame(left)
    tree_wrap.grid(row=5, column=0, sticky="nsew")
    tree_wrap.rowconfigure(0, weight=1)
    tree_wrap.columnconfigure(0, weight=1)

    tree = ttk.Treeview(tree_wrap, show="tree", selectmode="browse")
    vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")

    paned.add(left, weight=2)

    # --- right: inspector with contextual header + vertical split ---
    right = ttk.Frame(paned, padding=(6, 8, 10, 8))
    right.columnconfigure(0, weight=1)
    right.rowconfigure(1, weight=1)

    insp_header = ttk.Frame(right)
    insp_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))

    insp_title = ttk.Label(
        insp_header, text="No selection", style="InspectorTitle.TLabel"
    )
    insp_title.pack(side="left")
    insp_hint = ttk.Label(
        insp_header, text="Select a chunk on the left", style="InspectorHint.TLabel"
    )
    insp_hint.pack(side="left", padx=(8, 0))

    vpaned = ttk.PanedWindow(right, orient="vertical")
    vpaned.grid(row=1, column=0, sticky="nsew")

    # --- top: structure view ---
    struct_frame = ttk.Frame(vpaned)
    struct_frame.columnconfigure(0, weight=1)
    struct_frame.rowconfigure(1, weight=1)

    ttk.Label(struct_frame, text="STRUCTURE", style="Section.TLabel").grid(
        row=0, column=0, sticky="w", pady=(0, 2)
    )

    details_tree_wrap = ttk.Frame(struct_frame)
    details_tree_wrap.grid(row=1, column=0, sticky="nsew")
    details_tree_wrap.rowconfigure(0, weight=1)
    details_tree_wrap.columnconfigure(0, weight=1)

    details_tree = ttk.Treeview(
        details_tree_wrap, show="tree", selectmode="browse", style="Details.Treeview"
    )
    hvsb = ttk.Scrollbar(
        details_tree_wrap, orient="vertical", command=details_tree.yview
    )
    details_tree.configure(yscrollcommand=hvsb.set)

    details_tree.grid(row=0, column=0, sticky="nsew")
    hvsb.grid(row=0, column=1, sticky="ns")

    # --- bottom: data panel ---
    details_frame = ttk.Frame(vpaned)
    details_frame.columnconfigure(0, weight=1)
    details_frame.rowconfigure(1, weight=1)

    ttk.Label(details_frame, text="DATA", style="Section.TLabel").grid(
        row=0, column=0, sticky="w", pady=(4, 2)
    )

    details_text_wrap = ttk.Frame(details_frame)
    details_text_wrap.grid(row=1, column=0, sticky="nsew")
    details_text_wrap.rowconfigure(0, weight=1)
    details_text_wrap.columnconfigure(0, weight=1)

    details_label = tk.Text(
        details_text_wrap,
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
    for _tag in ("hex_offset", "hex_read", "hex_ascii"):
        details_label.tag_configure(_tag, foreground=COLORS[_tag])

    dlsb = ttk.Scrollbar(
        details_text_wrap, orient="vertical", command=details_label.yview
    )
    details_label.configure(yscrollcommand=dlsb.set)

    details_label.grid(row=0, column=0, sticky="nsew")
    dlsb.grid(row=0, column=1, sticky="ns")

    vpaned.add(struct_frame, weight=1)
    vpaned.add(details_frame, weight=1)

    paned.add(right, weight=3)

    # set initial sizes
    root.update()

    set_dark_titlebar(root)

    paned.sashpos(0, 460)
    vpaned.sashpos(0, 280)

    # maps structure-tree item ids to their (class_name, attribute)
    ATTR_NODES = {}

    def show_data_pane(show):
        attached = str(details_frame) in vpaned.panes()
        if show and not attached:
            vpaned.add(details_frame, weight=1)
            vpaned.update_idletasks()
            try:
                vpaned.sashpos(0, max(vpaned.winfo_height() // 2, 100))
            except tk.TclError:
                pass
        elif not show and attached:
            vpaned.forget(details_frame)

    def set_data_text(write_content):
        """Unlock the data panel, let `write_content` fill it, lock it again."""
        details_label.config(state="normal")
        details_label.delete("1.0", "end")
        write_content()
        details_label.config(state="disabled")

    HEX_DUMP_LIMIT = 64 * 1024

    def insert_hex_dump(data, width=16):
        shown = data[:HEX_DUMP_LIMIT]
        for off in range(0, len(shown), width):
            chunk = shown[off : off + width]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            details_label.insert("end", f"{off:08X}  ", "hex_offset")
            details_label.insert("end", f"{hex_part:<{width * 3 - 1}}  ", "hex_read")
            details_label.insert("end", ascii_part + "\n", "hex_ascii")
        if len(data) > HEX_DUMP_LIMIT:
            details_label.insert(
                "end",
                f"# ... truncated, {len(data) - HEX_DUMP_LIMIT} more bytes\n",
                "comment",
            )
        if not data:
            details_label.insert("end", "(no data)\n", "comment")

    def decode_attr_value(docs, data: bytes):
        """Decode attribute bytes per the documented data type.

        Returns display lines, or None when the type is unknown/undocumented.
        """
        dtype = (docs.get("data") or {}).get("type") if docs else None
        if not dtype or not data:
            return None

        try:
            if dtype == "GUID":
                return [f"{{{uuid.UUID(bytes=data[:16])}}}"]

            if dtype == "BOOLEAN":
                value = int.from_bytes(data[:1], byteorder="little")
                return [f"RWBool({value}) ({bool(value)})"]

            if dtype == "MESSAGE":
                value = Parser(data, endian="little").readPaddedCString().strip()
                return [f"{value} (message)" if value else "<No Message>"]

            if dtype == "RwUInt32":
                value = Parser(data, endian="little").readUint32()
                enum = docs["data"].get("list")
                if enum:
                    return [f"{enum['values'][value]} ({value})"]
                return [str(value)]

            if dtype == "RwV3d":
                buf = Parser(data, endian="little")
                return [f"({buf.readFloat()}, {buf.readFloat()}, {buf.readFloat()})"]

            if dtype == "RwReal":
                return [str(Parser(data, endian="little").readFloat())]

            if dtype == "RwChar":
                return [Parser(data, endian="little").readCString().strip()]

            if dtype == "RwRGBA":
                c = Parser(data, endian="little").readColor32()
                return [f"RGBA({c['r']}, {c['g']}, {c['b']}, {c['a']})"]

            if dtype == "Matrix4x4":
                m = RW_Matrix4x4.read(Parser(data, endian="little"))
                t = m.get_translation()
                return [
                    f"({row.x}, {row.y}, {row.z}, {row.w})"
                    for row in (m.row1, m.row2, m.row3, m.row4)
                ] + [f"Translation: ({t.x}, {t.y}, {t.z})"]

            if dtype == "CProtoActorStatsBlock":
                fields = parse_CProtoActor_attribute1(data)
                return [f"{k} = {v}" for k, v in fields.items()]

        except Exception as e:
            return [f"<failed to decode as {dtype}: {e}>"]

        return None

    def show_attribute(cls_name, attr):
        docs = CREATE_ENTITY_ATTRIBUTE_COMMANDS.get(cls_name, {}).get(attr.command)

        def write():
            header = [f"# {cls_name} — command {attr.command}"]
            if docs:
                header.append(f"# {docs.get('name')}")
                if docs.get("description"):
                    header.append(f"# {docs['description']}")
                dtype = (docs.get("data") or {}).get("type")
                if dtype:
                    header.append(f"# Type: {dtype}")
            header.append(f"# {len(attr.data)} bytes")
            details_label.insert("end", "\n".join(header) + "\n\n", "comment")

            decoded = decode_attr_value(docs, attr.data)
            if decoded:
                details_label.insert("end", "\n".join(decoded) + "\n\n")

            insert_hex_dump(attr.data)

        set_data_text(write)

    def show_data_hint(text):
        set_data_text(lambda: details_label.insert("end", text + "\n", "comment"))

    # nothing is selected yet, so start with just the structure pane
    show_data_pane(False)

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


    # contextual action, shown in the inspector header for entities
    tp_to_entity = ttk.Button(
        insp_header,
        text="Teleport to entity",
        style="Accent.TButton",
        command=tp_to_selected_entity,
    )

    def on_close():
        root.destroy()

    def populate(strm: stream.RW_StreamFile):
        TREE_ORDER.clear()
        SEARCH_TEXT.clear()
        ITEM_BEHAVIOUR.clear()

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
            guid = ""
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
                # braced form so a pasted "{...}" guid matches as well as a bare one
                guid = f"{{{sf.guid}}}"

            iid = tree.insert(
                "",
                "end",
                text=sf.streamfunc.name + label,
                values=(sf.header.type, sf.header.size),
                image=color,
            )

            STR_FUNCS[iid] = sf
            TREE_ORDER.append(iid)
            SEARCH_TEXT[iid] = f"{sf.streamfunc.name} {name} {behaviour} {guid}".lower()
            if sf.streamfunc == strfunc_func.sf_CreateEntity and behaviour:
                ITEM_BEHAVIOUR[iid] = behaviour

        behaviours = sorted(set(ITEM_BEHAVIOUR.values()))
        behaviour_combo["values"] = ("All", *behaviours)
        if behaviour_var.get() not in behaviour_combo["values"]:
            behaviour_var.set("All")

    with open(file_path, "rb") as f:
        strm = stream.load_stream(file_path)

        populate(strm)
        apply_filter()

    def on_select(event):
        global SELECTED

        sel = tree.selection()

        if not sel:
            return

        iid = sel[0]
        SELECTED = iid

        sf = STR_FUNCS[iid]

        insp_title.config(text=tree.item(iid, "text"))
        insp_hint.config(text=f"{sf.header.size} bytes")

        details_tree.delete(*details_tree.get_children())  # clear details tree
        ATTR_NODES.clear()

        tp_to_entity.pack_forget()
        if isinstance(sf, RW_sf_CreateEntity):
            tp_to_entity.pack(side="right")

            details_tree.insert("", "end", text=f"Behaviour: {sf.behaviour}", open=True)
            details_tree.insert("", "end", text=f"Entity ID: {{{sf.entityID}}}", open=True)
            details_tree.insert("", "end", text=f"Is Global: {sf.isGlobal}", open=True)
            for cls in sf.classes:
                cls_iid = details_tree.insert(
                    "", "end", text=f"Class: {cls.class_name}", open=True
                )
                for attr in cls.attributes:
                    commands = CREATE_ENTITY_ATTRIBUTE_COMMANDS.get(cls.class_name, {})
                    if commands.get(attr.command):
                        attr_iid = details_tree.insert(
                            cls_iid,
                            "end",
                            text=f"{attr.command} - {commands.get(attr.command).get("name")}, Data Size: {len(attr.data)} bytes"
                        )
                    else:
                        attr_iid = details_tree.insert(
                            cls_iid,
                            "end",
                            text=f"CMD: {attr.command}, Data Size: {len(attr.data)} bytes",
                        )
                    ATTR_NODES[attr_iid] = (cls.class_name, attr)

            show_data_pane(True)
            show_data_hint("# Select an attribute in Structure to inspect its data")

        elif isinstance(sf, RW_sf_LoadEmbeddedAsset):
            details_tree.insert("", "end", text=f"Name: {sf.name}")
            details_tree.insert("", "end", text=f"GUID: {{{sf.guid}}}")
            details_tree.insert("", "end", text=f"Type: {sf.type}")
            details_tree.insert("", "end", text=f"File Path: {sf.filePath}")
            details_tree.insert(
                "", "end", text=f"Deps: {sf.deps if sf.deps else '(none)'}"
            )
            details_tree.insert(
                "", "end", text=f"Data Size: {len(sf.data)} bytes"
            )

        elif isinstance(sf, RW_sf_PlacementNew):
            entries_iid = details_tree.insert(
                "", "end", text=f"Entries: {sf.entry_count}", open=True
            )
            for behaviour, instance_count in sf.entries:
                details_tree.insert(
                    entries_iid,
                    "end",
                    text=f"{behaviour} × {instance_count}",
                )

        elif isinstance(sf, RW_sf_SetDirectorsCameraMatrix):
            mtrx = details_tree.insert("", "end", text="Matrix (4x4)")
            details_tree.insert(mtrx, "end", text=f"Row 1: {sf.matrix.row1}")
            details_tree.insert(mtrx, "end", text=f"Row 2: {sf.matrix.row2}")
            details_tree.insert(mtrx, "end", text=f"Row 3: {sf.matrix.row3}")
            details_tree.insert(mtrx, "end", text=f"Row 4: {sf.matrix.row4}")

            details_tree.insert("", "end", text=f"FOV: {sf.fov}")

        elif isinstance(sf, RW_StreamFunc_NotImplemented):
            details_tree.insert("", "end", text=f"Data Size: {len(sf.raw_data)} bytes")
            details_tree.insert("", "end", text=f"Data: {sf.raw_data.hex()}")

        else:
            details_tree.insert("", "end", text=f"No details available for {sf.streamfunc.name}")

        if not isinstance(sf, RW_sf_CreateEntity):
            show_data_pane(False)

    tree.bind("<<TreeviewSelect>>", on_select)

    def on_attr_select(_event):
        sel = details_tree.selection()
        if not sel:
            return
        node = ATTR_NODES.get(sel[0])
        if node is None:
            if ATTR_NODES:  # entity is shown, but a non-attribute row is selected
                show_data_hint(
                    "# Select an attribute in Structure to inspect its data"
                )
            return
        show_attribute(*node)

    details_tree.bind("<<TreeviewSelect>>", on_attr_select)

    def reopen_file():
        global SELECTED

        tree.delete(*tree.get_children())
        STR_FUNCS.clear()
        details_tree.delete(*details_tree.get_children())
        ATTR_NODES.clear()
        show_data_pane(False)
        tp_to_entity.pack_forget()
        insp_title.config(text="No selection")
        insp_hint.config(text="Select a chunk on the left")
        strm = stream.load_stream(file_path)

        populate(strm)
        apply_filter()
        on_select(None)
        SELECTED = None

    reopen_btn = ttk.Button(
        header, text="⟳ Re-open", style="Header.TButton", command=reopen_file
    )
    reopen_btn.pack(side="right")

    def focus_search(_event=None):
        search_entry.focus_set()
        search_entry.select_range(0, "end")
        return "break"

    root.bind("<Control-f>", focus_search)
    root.bind("<Command-f>", focus_search)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
