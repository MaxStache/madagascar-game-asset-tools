import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from madagascar.savegame import read_save, write_save


DEFAULT_SAVE_PATH = (
    Path.home()
    / "Documents"
    / "Activision"
    / "Madagascar"
    / "Save"
    / "SaveGames.mem"
)


def browse_savefile():
    filepath = filedialog.askopenfilename(
        title="Select Madagascar Save File",
        initialdir=DEFAULT_SAVE_PATH.parent,
        initialfile=DEFAULT_SAVE_PATH.name,
        filetypes=[
            ("Madagascar Save Files", "*.mem"),
            ("All Files", "*.*"),
        ],
    )

    if filepath:
        savefile_var.set(filepath)


def patch_savefile():
    filepath = savefile_var.get()

    if not filepath:
        messagebox.showwarning(
            "No save file",
            "Please select a save file first.",
        )
        return

    slot_index = combo.current()

    if slot_index < 0:
        messagebox.showwarning(
            "No slot selected",
            "Please select a slot first.",
        )
        return

    confirmed = messagebox.askyesno(
        "WARNING - Irreversible",
        f"This will modify Slot {slot_index + 1} in:\n\n"
        f"{filepath}\n\n"
        "The existing save slot will be overwritten.\n"
        "This operation is IRREVERSIBLE.\n\n"
        "Make sure you have a backup of your save file before continuing.\n\n"
        "Do you want to continue?",
        icon="warning",
    )

    if not confirmed:
        return

    try:
        savegame = read_save(filepath)
        savegame.createDevSlot(slot_index)
        write_save(savegame, filepath)

        messagebox.showinfo(
            "Success",
            f"Slot {slot_index + 1} was successfully patched.",
        )

    except Exception as e:
        messagebox.showerror(
            "Patch failed",
            f"An error occurred:\n\n{e}",
        )


root = tk.Tk()
root.title("Madagascar Savegame Patcher")
root.geometry("600x350")

title = tk.Label(
    root,
    text="Madagascar Savegame Patcher",
    font=("Arial", 16, "bold"),
)
title.pack(pady=(20, 5))

description = tk.Label(
    root,
    text=(
        "Resets a slot in your savefile and sets all levels unlocked.\n"
        "Select a save file and the slot you want to modify."
    ),
    font=("Arial", 10),
    justify="center",
)
description.pack(pady=(0, 15))

warning = tk.Label(
    root,
    text=(
        "⚠ WARNING\n"
        "This operation is IRREVERSIBLE.\n"
        "Back up your save file before continuing."
    ),
    font=("Arial", 10, "bold"),
    justify="center",
)
warning.pack(pady=(0, 15))

# Save file
savefile_var = tk.StringVar(value=str(DEFAULT_SAVE_PATH))

file_frame = ttk.Frame(root)
file_frame.pack(fill="x", padx=20)

savefile_entry = ttk.Entry(
    file_frame,
    textvariable=savefile_var,
)
savefile_entry.pack(side="left", fill="x", expand=True)

browse_button = ttk.Button(
    file_frame,
    text="Browse...",
    command=browse_savefile,
)
browse_button.pack(side="left", padx=(8, 0))

# Slot selection
slot_frame = ttk.Frame(root)
slot_frame.pack(pady=15)

ttk.Label(
    slot_frame,
    text="Slot:",
).pack(side="left", padx=(0, 8))

combo = ttk.Combobox(
    slot_frame,
    state="readonly",
    values=("Slot 1", "Slot 2", "Slot 3", "Slot 4"),
    width=12,
)
combo.pack(side="left")
combo.current(0)

# Patch button
button = ttk.Button(
    root,
    text="Patch Slot",
    command=patch_savefile,
)
button.pack(pady=10)

root.mainloop()