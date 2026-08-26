"""Tkinter GUI that renders a texture dictionary as a grid of image previews."""

import ctypes as ct
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror

from PIL import Image, ImageTk

from madagascar.stream import load_stream
from madagascar.txd import loads_txd
from madagascar.sections.TEXTURENATIVE_0015 import RW_TextureNative

from tools.stream.theme import COLORS, configure_style

COLUMNS = 3
THUMB = 192  # preview box, in pixels
CARD_PAD = 10

TEXDICTIONARY_ASSET = "rwID_TEXDICTIONARY"


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
    value = ct.c_int(2)
    set_window_attribute(hwnd, rendering_policy, ct.byref(value), ct.sizeof(value))


def _checkerboard(size: tuple[int, int], square: int = 8) -> Image.Image:
    """Grey checker pattern, so transparent texels stay visible."""
    light = (60, 60, 60, 255)
    dark = (44, 44, 44, 255)

    board = Image.new("RGBA", size, dark)
    tile = Image.new("RGBA", (square, square), light)

    for y in range(0, size[1], square):
        for x in range(0, size[0], square):
            if ((x // square) + (y // square)) % 2 == 0:
                board.paste(tile, (x, y))

    return board


def _preview_mipmap(tex: RW_TextureNative) -> int:
    """Pick the cheapest mip level that is still big enough for a thumbnail.

    Mipmaps are stored largest first, so walking backwards finds the smallest
    level that does not need upscaling. Decoding is pure Python, and a level 0
    decode of every texture in a 250 entry dictionary is painfully slow.
    """
    mipmaps = tex.struct.mipmaps

    for index in range(len(mipmaps) - 1, -1, -1):
        mip = mipmaps[index]
        if max(mip.width, mip.height) >= THUMB:
            return index

    return 0


def _texture_image(tex: RW_TextureNative) -> Image.Image:
    """Decode a texture's preview mip level into an RGBA image."""
    index = _preview_mipmap(tex)
    mip = tex.struct.mipmaps[index]

    return Image.frombytes("RGBA", (mip.width, mip.height), bytes(tex.decode(index)))


def _thumbnail(image: Image.Image) -> Image.Image:
    """Fit an image into the thumbnail box, on a checkerboard backing."""
    fitted = image

    # Nearest keeps the pixel art of small UI textures readable; anything that
    # actually shrinks gets the smooth filter.
    resample = (
        Image.Resampling.NEAREST
        if max(fitted.size) <= THUMB
        else Image.Resampling.LANCZOS
    )

    scale = min(THUMB / fitted.width, THUMB / fitted.height)
    if scale != 1:
        fitted = fitted.resize(
            (max(int(fitted.width * scale), 1), max(int(fitted.height * scale), 1)),
            resample,
        )

    board = _checkerboard(fitted.size)
    board.alpha_composite(fitted)

    return board


def _format_summary(tex: RW_TextureNative) -> str:
    """One line describing how the texels are stored."""
    st = tex.struct

    if st.dxt_compression:
        level = 1 if st.dxt_compression in (1, 0x0C) else st.dxt_compression
        encoding = f"DXT{level}"
    elif st.palette:
        encoding = f"PAL{4 if st.raster_format.pal4 else 8}"
    else:
        encoding = st.raster_format.format.name.replace("FORMAT_", "")

    plural = "s" if st.mipmap_count != 1 else ""

    return (
        f"{st.platform_id.name} | {encoding} | {st.bitdeph}bpp | "
        f"{st.mipmap_count} mip{plural}"
    )


class TextureCard(ttk.Frame):
    """One grid cell: preview box, texture name, and a format line."""

    def __init__(self, master, tex: RW_TextureNative, index: int, on_open):
        super().__init__(master, style="Card.TFrame", padding=CARD_PAD)

        self.tex = tex
        self.index = index
        self.photo: ImageTk.PhotoImage | None = None
        self.image: Image.Image | None = None
        self._on_open = on_open

        st = tex.struct

        # Fixed pixel box for the preview. A Label's own width/height are
        # measured in characters, so the size has to come from a frame with
        # propagation switched off.
        box = tk.Frame(
            self, width=THUMB, height=THUMB, background=COLORS["panel_bg"]
        )
        box.pack_propagate(False)
        box.pack()

        self.preview = tk.Label(
            box,
            background=COLORS["panel_bg"],
            foreground=COLORS["hex_not_read"],
            text="...",
            compound="center",
            wraplength=THUMB - 16,
        )
        self.preview.pack(expand=True)

        self.name_label = ttk.Label(
            self,
            text=st.name or f"(unnamed #{index})",
            style="CardTitle.TLabel",
            anchor="center",
            wraplength=THUMB,
        )
        self.name_label.pack(fill="x", pady=(8, 0))

        ttk.Label(
            self,
            text=f"{st.width}x{st.height}",
            style="CardMeta.TLabel",
            anchor="center",
        ).pack(fill="x")

        ttk.Label(
            self,
            text=_format_summary(tex),
            style="CardMeta.TLabel",
            anchor="center",
            wraplength=THUMB,
        ).pack(fill="x")

        for widget in (self, self.preview, self.name_label):
            widget.bind("<Double-Button-1>", self._open)

    def _open(self, _event=None):
        if self.image is not None:
            self._on_open(self)

    def render(self):
        """Decode and show the preview. Called once per card."""
        st = self.tex.struct

        if not st.mipmaps:
            # Every raster the game ships has texels, so this is a damaged
            # file rather than a legitimate header-only entry.
            reason = (
                f"texels missing\ndeclares {st.texel_data_size} bytes"
                if not st.has_texel_data
                else "no mipmaps"
            )
            self.preview.configure(text=reason, foreground=COLORS["error"])
            return

        try:
            self.image = _texture_image(self.tex)
        except Exception as exc:  # an unsupported encoding shouldn't kill the grid
            self.preview.configure(
                text=f"decode failed\n{exc}",
                foreground=COLORS["error"],
            )
            return

        self.photo = ImageTk.PhotoImage(_thumbnail(self.image))
        self.preview.configure(image=self.photo, text="")


class TxdViewer:
    """The window: header bar, scrollable texture grid, status bar."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.cards: list[TextureCard] = []
        self.visible: list[TextureCard] = []
        self.pending: list[TextureCard] = []
        self.path: Path | None = None
        self.sources: list[tuple[str, bytes]] = []

        root.title("TXD Viewer")
        root.geometry("980x760")
        root.configure(background=COLORS["bg"])

        configure_style(root)
        self._configure_extra_styles()

        # -- header --
        header = ttk.Frame(root, style="Header.TFrame", padding=(14, 10))
        header.pack(fill="x")

        ttk.Label(header, text="TXD Viewer", style="AppTitle.TLabel").pack(side="left")

        self.file_label = ttk.Label(header, text="", style="FileName.TLabel")
        self.file_label.pack(side="left", padx=(12, 0))

        ttk.Button(
            header, text="Open...", style="Header.TButton", command=self.open_dialog
        ).pack(side="right")

        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self._layout())
        ttk.Entry(
            header, textvariable=self.search, style="Search.TEntry", width=24
        ).pack(side="right", padx=(0, 10))

        # Picks between the dictionaries a .stream carries; hidden for a
        # plain .txd, which only ever has one.
        self.source_picker = ttk.Combobox(
            header, state="readonly", style="Filter.TCombobox", width=26
        )
        self.source_picker.bind(
            "<<ComboboxSelected>>",
            lambda _e: self._show_source(self.source_picker.current()),
        )

        # -- scrollable grid --
        body = ttk.Frame(root, style="TFrame")
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            body, background=COLORS["bg"], highlightthickness=0, borderwidth=0
        )
        scrollbar = ttk.Scrollbar(
            body,
            orient="vertical",
            command=self.canvas.yview,
            style="Vertical.TScrollbar",
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.grid = ttk.Frame(self.canvas, style="TFrame", padding=CARD_PAD)
        self.grid_window = self.canvas.create_window(
            (0, 0), window=self.grid, anchor="nw"
        )

        self.grid.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self.grid_window, width=e.width),
        )
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

        for column in range(COLUMNS):
            self.grid.columnconfigure(column, weight=1, uniform="texcol")

        # -- status --
        status = ttk.Frame(root, style="Status.TFrame", padding=(14, 6))
        status.pack(fill="x")

        self.status_label = ttk.Label(
            status, text="No file loaded", style="Status.TLabel"
        )
        self.status_label.pack(side="left")

    def _configure_extra_styles(self):
        style = ttk.Style()

        style.configure("Card.TFrame", background=COLORS["panel_bg"])
        style.configure(
            "CardTitle.TLabel",
            background=COLORS["panel_bg"],
            foreground=COLORS["fg"],
        )
        style.configure(
            "CardMeta.TLabel",
            background=COLORS["panel_bg"],
            foreground=COLORS["muted"],
        )
        style.configure(
            "Caption.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["muted"],
        )

    # -- loading ------------------------------------------------------------

    @staticmethod
    def _read_sources(file_path: Path) -> list[tuple[str, bytes]]:
        """Collect every texture dictionary in ``file_path``, as raw bytes.

        A .stream carries its dictionaries as embedded assets, so they are
        taken straight out of the stream rather than from an unpacked asset
        folder on disk. Anything else is read as a standalone .txd.
        """
        if file_path.suffix.lower() == ".stream":
            stream = load_stream(file_path)

            return [
                (asset.name or asset.guid.hex, asset.data)
                for asset in stream.embeddedAssets()
                if asset.type == TEXDICTIONARY_ASSET
            ]

        return [(file_path.name, file_path.read_bytes())]

    def load(self, file_path: str | Path):
        file_path = Path(file_path)

        self.status_label.configure(text=f"Reading {file_path.name}...")
        self.root.update_idletasks()

        try:
            self.sources = self._read_sources(file_path)
        except Exception as exc:
            traceback.print_exc()
            showerror("TXD Viewer", f"Failed to read {file_path}:\n\n{exc}")
            self.status_label.configure(text=f"Failed to read {file_path.name}")
            return

        self.path = file_path
        self.file_label.configure(text=str(file_path))
        self.root.title(f"TXD Viewer - {file_path.name}")

        self.source_picker["values"] = [name for name, _ in self.sources]
        if len(self.sources) > 1:
            self.source_picker.current(0)
            self.source_picker.pack(side="right", padx=(0, 10))
        else:
            self.source_picker.pack_forget()

        if not self.sources:
            self._clear_cards()
            self.status_label.configure(
                text=f"{file_path.name} contains no texture dictionaries"
            )
            return

        self._show_source(0)

    def _clear_cards(self):
        for card in self.cards:
            card.destroy()

        self.cards = []
        self.visible = []
        self.pending = []

    def _show_source(self, index: int):
        """Parse one dictionary's bytes and rebuild the grid from it."""
        name, data = self.sources[index]

        self.status_label.configure(text=f"Parsing {name}...")
        self.root.update_idletasks()

        try:
            txd = loads_txd(data)
        except Exception as exc:
            traceback.print_exc()
            showerror("TXD Viewer", f"Failed to parse {name}:\n\n{exc}")
            self.status_label.configure(text=f"Failed to parse {name}")
            return

        self._clear_cards()

        self.cards = [
            TextureCard(self.grid, tex, position, self.show_full_size)
            for position, tex in enumerate(txd.textures)
        ]
        self.pending = list(self.cards)

        self._layout()
        self.canvas.yview_moveto(0)
        self.root.after(1, self._render_pending)

    def _layout(self):
        """(Re)place the cards matching the search box into the 3 wide grid."""
        needle = self.search.get().strip().lower()

        self.visible = [
            card
            for card in self.cards
            if not needle or needle in card.tex.struct.name.lower()
        ]

        for card in self.cards:
            card.grid_forget()

        for position, card in enumerate(self.visible):
            card.grid(
                row=position // COLUMNS,
                column=position % COLUMNS,
                padx=CARD_PAD // 2,
                pady=CARD_PAD // 2,
                sticky="n",
            )

        self._update_status()

    def _render_pending(self):
        """Decode previews in time boxed batches so the window stays alive."""
        if not self.pending:
            self._update_status()
            return

        deadline = time.monotonic() + 0.05  # ~50 ms of work per tick

        while self.pending and time.monotonic() < deadline:
            self.pending.pop(0).render()

        self._update_status()
        self.root.after(1, self._render_pending)

    def _update_status(self):
        if self.path is None:
            self.status_label.configure(text="No file loaded")
            return

        if not self.cards:
            self.status_label.configure(text="Empty dictionary - 0 textures")
            return

        shown = len(self.visible)
        total = len(self.cards)
        text = f"{shown} of {total} textures" if shown != total else f"{total} textures"

        if self.pending:
            text += f" | decoding {total - len(self.pending)}/{total}"
        else:
            text += " | double-click a preview for full size"

        self.status_label.configure(text=text)

    # -- actions ------------------------------------------------------------

    def open_dialog(self):
        file_path = askopenfilename(
            title="Open texture dictionary",
            filetypes=[
                ("Texture dictionary or stream", "*.txd *.stream"),
                ("Texture dictionary", "*.txd"),
                ("RenderWare Studio stream", "*.stream"),
                ("All files", "*.*"),
            ],
        )
        if file_path:
            self.load(file_path)

    def show_full_size(self, card: TextureCard):
        """Pop the selected texture up at 1:1, on a checkerboard."""
        assert card.image is not None

        top = tk.Toplevel(self.root)
        top.title(card.tex.struct.name or f"texture #{card.index}")
        top.configure(background=COLORS["bg"])

        board = _checkerboard(card.image.size)
        board.alpha_composite(card.image)
        photo = ImageTk.PhotoImage(board)

        label = tk.Label(top, image=photo, background=COLORS["bg"], borderwidth=0)
        label.image = photo  # keep a reference alive
        label.pack(padx=12, pady=12)

        ttk.Label(
            top,
            text=f"{card.image.width}x{card.image.height} | {_format_summary(card.tex)}",
            style="Caption.TLabel",
        ).pack(pady=(0, 12))

        top.bind("<Escape>", lambda _e: top.destroy())
        set_dark_titlebar(top)

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-event.delta // 120, "units")


def run(file_path: str | Path | None = None):
    """Open ``file_path`` and launch the window."""
    root = tk.Tk()

    viewer = TxdViewer(root)
    set_dark_titlebar(root)

    if file_path:
        root.after(10, lambda: viewer.load(file_path))
    else:
        root.after(10, viewer.open_dialog)

    root.mainloop()
