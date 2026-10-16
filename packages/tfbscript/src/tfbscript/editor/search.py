# pyright: basic

from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

ROW_OBJECT_NAME = "tfbRow"

MATCH_BG = "#FFF2A8"
CURRENT_MATCH_BG = "#FFC63F"

# Space kept around a row's fields so a highlight doesn't hug the text
ROW_PADDING = 3


def row_text(layout: QHBoxLayout) -> str:
    """Flattens a rendered row into one searchable string.

    Reads the already-built widgets rather than the opcode itself: rendering a
    reference needs the enclosing-op stack, which only exists while the tree is
    being populated.
    """
    parts: list[str] = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item is None:
            continue
        widget = item.widget()
        if isinstance(widget, (QLabel, QPushButton)):
            parts.append(widget.text())
    return " ".join(parts)


@dataclass
class SearchEntry:
    item: QTreeWidgetItem
    content: QWidget
    _text: str = field(default="", repr=False)

    def text(self) -> str:
        return self._text

    def set_text(self, text: str) -> None:
        self._text = text.lower()


class SearchBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Find")
        self.edit.setClearButtonEnabled(False)

        self.status = QLabel("")
        self.status.setMinimumWidth(90)
        self.status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.close_button = QPushButton("Close")

        layout.addWidget(QLabel("Find:"))
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.status)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.close_button)


class TreeSearch:
    """Incremental find over the rows of the opcode tree.

    Rows are custom item widgets, so matching runs against the flattened text of
    each opcode and the hit is shown by tinting the row's container widget.
    """

    def __init__(self, tree: QTreeWidget, bar: SearchBar, entries: list[SearchEntry]):
        self.tree = tree
        self.bar = bar
        self.entries = entries
        self.matches: list[int] = []
        self.current = -1

        for entry in entries:
            entry.content.setObjectName(ROW_OBJECT_NAME)
            entry.content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        bar.edit.textChanged.connect(self._on_query_changed)
        bar.edit.returnPressed.connect(self.next_match)
        bar.next_button.clicked.connect(self.next_match)
        bar.prev_button.clicked.connect(self.previous_match)
        bar.close_button.clicked.connect(self.close)

        shift_return = QShortcut(
            QKeySequence(Qt.KeyboardModifier.ShiftModifier | Qt.Key.Key_Return), bar.edit
        )
        shift_return.setContext(Qt.ShortcutContext.WidgetShortcut)
        shift_return.activated.connect(self.previous_match)

        escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), bar)
        escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        escape.activated.connect(self.close)

        bar.hide()

    def open(self) -> None:
        self.bar.show()
        self.bar.edit.setFocus()
        self.bar.edit.selectAll()
        self._search(self.bar.edit.text())

    def close(self) -> None:
        self._clear_highlights()
        self.matches = []
        self.current = -1
        self.bar.hide()

    def next_match(self) -> None:
        self._step(1)

    def previous_match(self) -> None:
        self._step(-1)

    def _on_query_changed(self, query: str) -> None:
        self._search(query)

    def _search(self, query: str) -> None:
        self._clear_highlights()

        needle = query.strip().lower()
        if not needle:
            self.matches = []
            self.current = -1
            self.bar.status.setText("")
            return

        self.matches = [
            i for i, entry in enumerate(self.entries) if needle in entry.text()
        ]
        self.current = 0 if self.matches else -1
        self._apply_highlights()
        self._reveal_current()
        self._update_status()

    def _step(self, delta: int) -> None:
        if not self.matches:
            return
        self.current = (self.current + delta) % len(self.matches)
        self._apply_highlights()
        self._reveal_current()
        self._update_status()

    def _clear_highlights(self) -> None:
        for index in self.matches:
            self.entries[index].content.setStyleSheet("")

    def _apply_highlights(self) -> None:
        for position, index in enumerate(self.matches):
            color = CURRENT_MATCH_BG if position == self.current else MATCH_BG
            self.entries[index].content.setStyleSheet(
                f"#{ROW_OBJECT_NAME} {{ background-color: {color}; }}"
            )

    def _reveal_current(self) -> None:
        if self.current < 0:
            return
        item = self.entries[self.matches[self.current]].item

        parent = item.parent()
        while parent is not None:
            parent.setExpanded(True)
            parent = parent.parent()

        self.tree.scrollToItem(
            item, QAbstractItemView.ScrollHint.PositionAtCenter
        )

    def _update_status(self) -> None:
        if not self.matches:
            self.bar.status.setText("No results")
        else:
            self.bar.status.setText(f"{self.current + 1} of {len(self.matches)}")
