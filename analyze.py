import tkinter as tk
from tkinter import ttk
from formats import sections
from formats.rw_basics import RWHeader
from formats.rwConstants import RWSectionType
from formats.lib.parser import Parser

CONTAINER_CHUNKS = {
    RWSectionType.rwID_CLUMP.value,
    RWSectionType.rwID_Frame.value,
    RWSectionType.rwID_FRAMELIST.value,
    RWSectionType.rwID_GEOMETRY.value,
    RWSectionType.rwID_GEOMETRYLIST.value,
    RWSectionType.rwID_TEXDICTIONARY.value,
    RWSectionType.rwID_TEXTURENATIVE.value,
    RWSectionType.rwID_EXTENSION.value,
    RWSectionType.rwID_MATERIAL.value,
    RWSectionType.rwID_MATLIST.value,
    RWSectionType.rwID_ATOMIC.value,
    RWSectionType.rwID_TEXTURE.value,
    RWSectionType.rwID_LIGHT.value,
}


def read_recursive(parser, depth=0):
    header = RWHeader.read(parser)
    data = parser.read(header.size)

    children = []
    if header.type in CONTAINER_CHUNKS:
        subparser = Parser(data, endian="little")
        while subparser.remaining() > 0:
            children.append(read_recursive(subparser, depth + 1))

    return header, data, children


def hexdump(data, width=8):
    lines = []

    for off in range(0, len(data), width):
        chunk = data[off : off + width]
        hex_part = " ".join(f"{b:02X}" for b in chunk).ljust(width * 3 - 1)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{off:08X}  {hex_part}  {ascii_part}")

    return "\n".join(lines)


leaf_bytes = {}
tree_headers = {}


root = tk.Tk()
root.title("RW Tree")
root.geometry("900x500")


# --- icons ---
padding_x = 5
size = 15

green_dot = tk.PhotoImage(width=size + padding_x * 2, height=size)
blue_dot = tk.PhotoImage(width=size + padding_x * 2, height=size)
gray_dot = tk.PhotoImage(width=size + padding_x * 2, height=size)

for x in range(size):
    for y in range(size):
        if (x - size // 2) ** 2 + (y - size // 2) ** 2 <= (size // 2 - 1) ** 2:
            green_dot.put("#00D100", (x + padding_x, y))
            blue_dot.put("#1D9BF2", (x + padding_x, y))
            gray_dot.put("#9C9C9C", (x + padding_x, y))


def populate(tree, parent, node):
    header, data, children = node

    sect = RWSectionType(header.type)
    label = f"{sect.name}  (0x{header.type:X}, {header.size} B)"

    color = blue_dot if children else green_dot
    is_implemented = sections.SECTION_REGISTRY.get(header.type) is not sections.RW_Section_NotImplemented

    iid = tree.insert(
        parent, "end", text=label, image=color if is_implemented else gray_dot, open=True
    )

    leaf_bytes[iid] = data
    tree_headers[iid] = header

    for child in children:
        populate(tree, iid, child)


# --- main horizontal split ---
paned = ttk.PanedWindow(root, orient="horizontal")
paned.pack(fill="both", expand=True)


# --- left tree ---
left = ttk.Frame(paned)

tree = ttk.Treeview(left, show="tree")

vsb = ttk.Scrollbar(left, orient="vertical", command=tree.yview)

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
    background="#ffffff",
    foreground="#3b3b3b",
)

hvsb = ttk.Scrollbar(hex_frame, orient="vertical", command=hexview.yview)

hexview.configure(yscrollcommand=hvsb.set)

hvsb.pack(side="right", fill="y")
hexview.pack(side="left", fill="both", expand=True)


# --- bottom: details panel ---
details_frame = ttk.Frame(right)

details_label = tk.Text(
    details_frame,
)

details_label.pack(anchor="nw", padx=5, pady=5)


right.add(hex_frame, weight=3)
right.add(details_frame, weight=1)

paned.add(right, weight=1)


# set initial sizes
root.update()

paned.sashpos(0, 400)
right.sashpos(0, 300)

def pretty_object(obj, indent=0):
    """Generate a nice multiline representation of an object's properties."""
    prefix = " " * indent
    cls_name = type(obj).__name__

    lines = [f"{cls_name}("]

    # Get properties/fields
    if hasattr(obj, "__dataclass_fields__"):
        fields = obj.__dataclass_fields__.keys()
        values = {name: getattr(obj, name) for name in fields}
    else:
        values = vars(obj)

    for name, value in values.items():
        formatted = pretty_value(value, indent + 4)
        lines.append(f"{prefix}    {name}={formatted},")

    lines.append(f"{prefix})")

    return "\n".join(lines)


def pretty_value(value, indent):
    """Format nested values."""
    if hasattr(value, "__dict__") or hasattr(value, "__dataclass_fields__"):
        return pretty_object(value, indent)

    if isinstance(value, list):
        if not value:
            return "[]"

        items = [
            " " * (indent + 4) + pretty_value(v, indent + 4)
            for v in value
        ]

        return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"

    if isinstance(value, bytes):
        return repr(value)

    return repr(value)
    
def on_select(event):
    sel = tree.selection()

    if not sel:
        return

    iid = sel[0]

    hexview.config(state="normal")
    hexview.delete("1.0", "end")

    if iid in leaf_bytes:
        hexview.insert("1.0", hexdump(leaf_bytes[iid]))


    section = sections.SECTION_REGISTRY.get(tree_headers[iid].type)
    print("------------------------------------  READ ------------------------------------")
    abc = section.read(Parser(tree_headers[iid].pack() + leaf_bytes[iid], endian="little"))
    print("-------------------------------------------------------------------------------")

    details_label.delete("1.0", "end")          # remove existing content
    details_label.insert("1.0", pretty_object(abc))  # insert new content

    hexview.config(state="disabled")


tree.bind("<<TreeviewSelect>>", on_select)

FILE = "Levels/KingOfNY/45_janitor.dff"
#FILE = "Levels/KingOfNY/48_janitor_walk.anm"

with open(FILE, "rb") as f:
    parser = Parser(f.read(), endian="little")

    populate(tree, "", read_recursive(parser))


root.mainloop()
