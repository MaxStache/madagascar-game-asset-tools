"""The text widget: a plain editor with a line-number gutter.

Compile errors carry a line and a column, so the gutter earns its place --
"12:7: unknown flow control" is only useful next to line numbers.
"""

# pyright: basic

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFontDatabase,
    QPainter,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from tfbpseudo.editor.theme import DEFAULT, Theme


class LineNumbers(QWidget):
    """The gutter down the left of the editor."""

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, event) -> None:
        self.editor.paint_gutter(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None, theme: Theme = DEFAULT):
        super().__init__(parent)
        self.theme = theme

        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(12)
        self.setFont(font)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.gutter = LineNumbers(self)
        self.error_line: int | None = None  # 1-based, from a failed compile

        self.blockCountChanged.connect(self.update_gutter_width)
        self.updateRequest.connect(self.update_gutter)
        self.cursorPositionChanged.connect(self.highlight_lines)
        self.textChanged.connect(self.clear_error)

        self.update_gutter_width()
        self.highlight_lines()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.highlight_lines()
        self.gutter.update()

    # ----- the gutter -----

    def gutter_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_gutter_width(self) -> None:
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def update_gutter(self, rect: QRect, dy: int) -> None:
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_gutter_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        area = self.contentsRect()
        self.gutter.setGeometry(
            QRect(area.left(), area.top(), self.gutter_width(), area.height())
        )

    def paint_gutter(self, event) -> None:
        painter = QPainter(self.gutter)
        painter.fillRect(event.rect(), QColor(self.theme.gutter))

        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        current = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = block.blockNumber() + 1
                painter.setPen(
                    QColor(
                        self.theme.gutter_current
                        if block.blockNumber() == current
                        else self.theme.gutter_text
                    )
                )
                painter.drawText(
                    0,
                    int(top),
                    self.gutter.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number),
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

    # ----- the line under the cursor, and the one an error points at -----

    def highlight_lines(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(self.theme.current_line))
            selection.format.setProperty(
                QTextFormat.Property.FullWidthSelection, True
            )
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            selections.append(selection)

        # Last, so it wins over the current-line tint -- the cursor is put on
        # the offending line, so the two are usually the same line.
        if self.error_line is not None:
            selections.append(self.line_selection(self.error_line, QColor(self.theme.error_line)))

        self.setExtraSelections(selections)
        self.gutter.update()

    def line_selection(self, line: int, color: QColor) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(color)
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = QTextCursor(self.document().findBlockByNumber(line - 1))
        selection.cursor.clearSelection()
        return selection

    def show_error_at(self, line: int, col: int) -> None:
        """Mark the line an error points at and put the cursor on it."""
        block = self.document().findBlockByNumber(max(0, line - 1))
        if not block.isValid():
            return

        self.error_line = line

        cursor = QTextCursor(block)
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.MoveAnchor,
            max(0, col - 1),
        )
        self.setTextCursor(cursor)
        self.centerCursor()
        self.highlight_lines()

    def clear_error(self) -> None:
        if self.error_line is not None:
            self.error_line = None
            self.highlight_lines()
