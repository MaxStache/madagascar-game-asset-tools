import tkinter as tk
from tkinter import ttk


class StatusTree(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Status Tree")
        self.geometry("400x300")

        self.tree = ttk.Treeview(self)
        self.tree.pack(fill="both", expand=True)

        # Keep references to images!
        self.icons = {
            "green": self.create_dot("green"),
            "yellow": self.create_dot("orange"),
            "red": self.create_dot("red"),
            "gray": self.create_dot("gray"),
        }

        # Example data
        server = self.add_node(
            "",
            "Server",
            status="green",
            open=True,
        )

        self.add_node(server, "Database", status="green")
        self.add_node(server, "API", status="yellow")
        self.add_node(server, "Cache", status="red")

        app2 = self.add_node(
            "",
            "Application",
            status="yellow",
            open=True,
        )

        self.add_node(app2, "Worker 1", status="green")
        self.add_node(app2, "Worker 2", status="gray")

    def create_dot(self, color, size=12):
        img = tk.PhotoImage(width=size, height=size)

        center = size // 2
        radius = size // 2 - 1

        for x in range(size):
            for y in range(size):
                dx = x - center
                dy = y - center

                if dx * dx + dy * dy <= radius * radius:
                    img.put(color, (x, y))

        return img

    def add_node(self, parent, text, status="gray", **kwargs):
        return self.tree.insert(
            parent,
            "end",
            text=text,
            image=self.icons[status],
            **kwargs
        )


if __name__ == "__main__":
    StatusTree().mainloop()