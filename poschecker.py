import tkinter as tk
from tkinter import ttk

from formats.lib.game_memory import PlayerPosition


UPDATE_MS = 50


class PositionViewer:
    def __init__(self):
        self.player = PlayerPosition("Game.exe")

        self.root = tk.Tk()
        self.root.title("Player Position")
        self.root.geometry("360x180")
        self.root.resizable(False, False)

        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        pos_frame = ttk.LabelFrame(
            main,
            text="Player Position",
            padding=10,
        )
        pos_frame.pack(fill="x")

        self.value_labels = {}
        self.entries = {}

        for row, axis in enumerate(("X", "Y", "Z")):
            ttk.Label(
                pos_frame,
                text=axis,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 10),
                pady=4,
            )

            value = ttk.Label(
                pos_frame,
                text="0.000",
                font=("Consolas", 11),
                width=12,
                anchor="e",
            )
            value.grid(
                row=row,
                column=1,
                sticky="ew",
                padx=(0, 10),
            )

            entry = ttk.Entry(pos_frame)
            entry.grid(
                row=row,
                column=2,
                sticky="ew",
            )

            self.value_labels[axis] = value
            self.entries[axis] = entry

        pos_frame.columnconfigure(1, weight=1)
        pos_frame.columnconfigure(2, weight=1)

        ttk.Button(
            main,
            text="Set Position",
            command=self.set_position,
        ).pack(
            fill="x",
            pady=(12, 0),
        )

        self.update_position()

        self.root.mainloop()

    def update_position(self):
        try:
            x, y, z = self.player.position

            self.value_labels["X"].config(text=f"{x:10.3f}")
            self.value_labels["Y"].config(text=f"{y:10.3f}")
            self.value_labels["Z"].config(text=f"{z:10.3f}")

        except Exception as e:
            for label in self.value_labels.values():
                label.config(text="Error")

            print(e)

        self.root.after(
            UPDATE_MS,
            self.update_position,
        )

    def set_position(self):
        try:
            values = {}

            for axis in ("X", "Y", "Z"):
                value = self.entries[axis].get().strip()

                if value:
                    values[axis.lower()] = float(value)

            self.player.set_position(**values)

        except Exception as e:
            print(e)


if __name__ == "__main__":
    PositionViewer()