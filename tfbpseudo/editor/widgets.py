"""The text widget: a plain editor with a line-number gutter.

Compile errors carry a line and a column, so the gutter earns its place --
"12:7: unknown flow control" is only useful next to line numbers.

Scripts nest a few levels deep -- prescript, behavior, flow, else -- so the
editor draws a rule down every level of indentation, keeps the indent when you
press Return, and marks the brace matching the one under the cursor. Anything
it indents is the four spaces the decompiler writes.

The line commands -- comment, indent, move, duplicate -- work on whole lines
and keep whatever was selected selected, so they can be leant on.
"""

# pyright: basic

from collections.abc import Iterable
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFontDatabase,
    QPainter,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QToolTip, QWidget

from tfbpseudo.editor.completions import help_at
from tfbpseudo.editor.theme import DEFAULT, Theme

if TYPE_CHECKING:
    from tfbpseudo.editor.completer import Completer

INDENT = "    "  # what the decompiler writes for one level
COMMENT = "// "  # what a commented-out line starts with


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
        # Every line a problem points at, 1-based. The panel checks as you
        # type and hands over the whole list, so they are all tinted at once.
        self.error_lines: list[int] = []

        # Set by the completer when one is attached, since typing is what
        # drives it and every key comes through here first.
        self.completer: "Completer | None" = None

        # Owned by the find box, kept here because every repaint of the
        # extra selections has to put them back.
        self.search_selections: list[QTextEdit.ExtraSelection] = []

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

    # ----- the rule down each level of indentation -----

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self.paint_indent_guides(event)

    def paint_indent_guides(self, event) -> None:
        painter = QPainter(self.viewport())
        painter.setPen(QColor(self.theme.indent_guide))

        step = self.fontMetrics().horizontalAdvance(" ") * len(INDENT)
        margin = self.document().documentMargin()

        block = self.firstVisibleBlock()
        offset = self.contentOffset()
        top = self.blockBoundingGeometry(block).translated(offset).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                left = self.blockBoundingGeometry(block).translated(offset).left()
                for level in range(guide_depth(block)):
                    x = int(left + margin + level * step)
                    painter.drawLine(x, int(top), x, int(bottom) - 1)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

    # ----- typing -----

    def keyPressEvent(self, event) -> None:
        # While the completion popup is up it has first claim on Return, Tab
        # and Escape -- ignoring them here is what hands them over.
        if self.completer is not None and self.completer.takes(event):
            event.ignore()
            return

        plain = event.modifiers() in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.KeypadModifier,
        )
        if plain and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.insert_newline()
            return

        # Tab is indentation, never a tab character: the decompiler writes
        # spaces and a stray tab would not line up with what is around it.
        if plain and event.key() == Qt.Key.Key_Tab:
            self.indent_lines() if self.textCursor().hasSelection() else (
                self.insert_indent()
            )
            return

        if event.key() == Qt.Key.Key_Backtab:
            self.dedent_lines()
            return

        super().keyPressEvent(event)

        if self.completer is not None:
            self.completer.typed(event.text())

    def insert_newline(self) -> None:
        """Return, landing on the indent of the line it was pressed on.

        A line that opens a block indents one level further, and a closing
        brace already sitting after the cursor is pushed down to the outer
        level, so Return between a pair of braces opens the block out.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if cursor.hasSelection():
            cursor.removeSelectedText()

        text = cursor.block().text()
        before = text[: cursor.positionInBlock()]
        after = text[cursor.positionInBlock() :]

        # Truncated at the cursor: Return pressed inside the indentation of a
        # line carries only the indent to its left.
        indent = before[: len(before) - len(before.lstrip())]
        opening = before.rstrip().endswith("{")

        cursor.insertText("\n" + indent + (INDENT if opening else ""))

        if opening and after.lstrip().startswith("}"):
            landed = cursor.position()
            cursor.insertText("\n" + indent)
            cursor.setPosition(landed)

        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    # ----- what the mouse is resting on -----

    def viewportEvent(self, event) -> bool:
        """The tooltip for whatever the mouse has stopped over.

        On the viewport rather than the widget, because that is what the
        mouse is actually over and what `cursorForPosition` measures from.
        """
        if event.type() == QEvent.Type.ToolTip:
            cursor = self.cursorForPosition(event.pos())
            said = help_at(self.toPlainText(), cursor.position())

            if said:
                QToolTip.showText(event.globalPos(), said, self)
            else:
                QToolTip.hideText()

            return True

        return super().viewportEvent(event)

    # ----- commands over whole lines -----

    def line_span(self, cursor: QTextCursor) -> tuple[int, int]:
        """The first and last block a selection touches, as block numbers.

        A selection ending at the very start of a line does not count as
        reaching that line -- it is the line above that was dragged over.
        """
        first = self.document().findBlock(cursor.selectionStart()).blockNumber()
        end = self.document().findBlock(cursor.selectionEnd())
        last = end.blockNumber()

        if last > first and cursor.selectionEnd() == end.position():
            last -= 1

        return first, last

    def lines_in(self, first: int, last: int) -> list[str]:
        document = self.document()
        return [
            document.findBlockByNumber(number).text()
            for number in range(first, last + 1)
        ]

    def replace_lines(self, first: int, last: int, lines: list[str]) -> None:
        """Put `lines` in place of blocks `first` to `last`, in one edit."""
        document = self.document()
        start = document.findBlockByNumber(first)
        end = document.findBlockByNumber(last)

        cursor = QTextCursor(start)
        cursor.beginEditBlock()
        cursor.setPosition(start.position())
        cursor.setPosition(
            end.position() + end.length() - 1, QTextCursor.MoveMode.KeepAnchor
        )
        cursor.insertText("\n".join(lines))
        cursor.endEditBlock()

    def select_lines(self, first: int, last: int) -> None:
        document = self.document()
        end = document.findBlockByNumber(last)

        cursor = QTextCursor(document.findBlockByNumber(first))
        cursor.setPosition(
            end.position() + end.length() - 1, QTextCursor.MoveMode.KeepAnchor
        )
        self.setTextCursor(cursor)

    def toggle_comment(self) -> None:
        """Comment the selected lines out, or put them back.

        They go back in as they were only if nothing else was done to them in
        between: the marker goes on at the shallowest indent of the lot, so
        the block keeps its shape rather than being flattened to the margin.
        """
        cursor = self.textCursor()
        first, last = self.line_span(cursor)
        lines = self.lines_in(first, last)
        written = [line for line in lines if line.strip()]

        if not written:
            return

        if all(line.lstrip().startswith("//") for line in written):
            lines = [uncomment(line) for line in lines]
        else:
            column = min(len(line) - len(line.lstrip()) for line in written)
            lines = [
                line[:column] + COMMENT + line[column:] if line.strip() else line
                for line in lines
            ]

        self.replace_lines(first, last, lines)
        self.select_lines(first, last)

    def indent_lines(self) -> None:
        cursor = self.textCursor()
        first, last = self.line_span(cursor)
        lines = [
            INDENT + line if line.strip() else line
            for line in self.lines_in(first, last)
        ]

        self.replace_lines(first, last, lines)
        self.select_lines(first, last)

    def dedent_lines(self) -> None:
        cursor = self.textCursor()
        first, last = self.line_span(cursor)
        lines = [dedent(line) for line in self.lines_in(first, last)]

        self.replace_lines(first, last, lines)
        self.select_lines(first, last)

    def insert_indent(self) -> None:
        """Tab with nothing selected: on to the next stop, in spaces."""
        cursor = self.textCursor()
        width = len(INDENT) - cursor.positionInBlock() % len(INDENT)
        cursor.insertText(" " * width)

    def move_lines(self, down: bool) -> None:
        """Take the selected lines past the line above or below them."""
        cursor = self.textCursor()
        selected = cursor.hasSelection()
        column = cursor.positionInBlock()
        first, last = self.line_span(cursor)
        step = 1 if down else -1

        document = self.document()
        neighbour = document.findBlockByNumber(last + 1 if down else first - 1)
        if not neighbour.isValid():
            return

        lines = self.lines_in(first, last)

        # The whole run, the neighbour included, written back the other way
        # round: one edit, so one undo takes the move back.
        if down:
            self.replace_lines(first, last + 1, [neighbour.text(), *lines])
        else:
            self.replace_lines(first - 1, last, [*lines, neighbour.text()])

        if selected:
            self.select_lines(first + step, last + step)
        else:
            block = document.findBlockByNumber(first + step)
            landed = QTextCursor(block)
            landed.setPosition(block.position() + min(column, len(block.text())))
            self.setTextCursor(landed)

    def duplicate_lines(self) -> None:
        """A copy of the selected lines, below them, with the copy selected."""
        cursor = self.textCursor()
        selected = cursor.hasSelection()
        column = cursor.positionInBlock()
        first, last = self.line_span(cursor)
        lines = self.lines_in(first, last)

        self.replace_lines(first, last, [*lines, *lines])

        copied = last + 1, last + (last - first) + 1
        if selected:
            self.select_lines(*copied)
        else:
            block = self.document().findBlockByNumber(copied[0])
            landed = QTextCursor(block)
            landed.setPosition(block.position() + min(column, len(block.text())))
            self.setTextCursor(landed)

    # ----- the brace matching the one under the cursor -----

    def brace_selections(self) -> list[QTextEdit.ExtraSelection]:
        """Both braces of the pair the cursor is on, or nothing."""
        text = self.toPlainText()
        position = self.textCursor().position()

        here = brace_at(text, position)
        if here is None:
            return []

        other = matching_brace(text, here)
        if other is None:
            return []

        return [self.character_selection(at) for at in (here, other)]

    def character_selection(self, position: int) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(self.theme.brace))

        cursor = QTextCursor(self.document())
        cursor.setPosition(position)
        cursor.setPosition(position + 1, QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor

        return selection

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

        # Last, so they win over the current-line tint -- the cursor is often
        # on one of the offending lines, being what put it there.
        selections.extend(
            self.line_selection(line, QColor(self.theme.error_line))
            for line in self.error_lines
        )

        selections.extend(self.brace_selections())

        # Later still: a match has to stay visible on the line the cursor is
        # on, which is exactly where find has just put it.
        selections.extend(self.search_selections)

        self.setExtraSelections(selections)
        self.gutter.update()

    def line_selection(self, line: int, color: QColor) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(color)
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = QTextCursor(self.document().findBlockByNumber(line - 1))
        selection.cursor.clearSelection()
        return selection

    def set_search_selections(
        self, selections: list[QTextEdit.ExtraSelection]
    ) -> None:
        """Replace the find box's highlights. Pass an empty list to drop them."""
        self.search_selections = list(selections)
        self.highlight_lines()

    def mark_errors(self, lines: Iterable[int]) -> None:
        """Tint every line a problem points at, leaving the cursor where it is.

        This is what the panel's check uses: it runs while a line is being
        typed, and taking the cursor away mid-word would be unusable. The
        lines given replace the ones tinted now, so an empty list clears them.
        """
        self.error_lines = [
            line
            for line in lines
            if self.document().findBlockByNumber(max(0, line - 1)).isValid()
        ]
        self.highlight_lines()

    def go_to_line(self, line: int, col: int = 1) -> bool:
        """Put the cursor on a line and bring it into view, saying if it is
        there at all."""
        block = self.document().findBlockByNumber(max(0, line - 1))
        if not block.isValid():
            return False

        cursor = QTextCursor(block)
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.MoveAnchor,
            max(0, col - 1),
        )
        self.setTextCursor(cursor)
        self.centerCursor()
        return True

    def show_error_at(self, line: int, col: int) -> None:
        """Put the cursor on the line a problem points at, tinting it too.

        The rest stay tinted: going to one problem is not a claim about the
        others.
        """
        if not self.go_to_line(line, col):
            return

        if line not in self.error_lines:
            self.error_lines.append(line)

        self.highlight_lines()

    def clear_error(self) -> None:
        if self.error_lines:
            self.error_lines = []
            self.highlight_lines()


def uncomment(line: str) -> str:
    """`line` without the comment marker it was commented out with."""
    indent = line[: len(line) - len(line.lstrip())]
    rest = line.lstrip()

    if not rest.startswith("//"):
        return line

    rest = rest[2:]
    return indent + (rest[1:] if rest.startswith(" ") else rest)


def dedent(line: str) -> str:
    """`line` one level shallower, by however much of a level it has."""
    if line.startswith("\t"):
        return line[1:]

    width = len(line) - len(line.lstrip(" "))
    return line[min(width, len(INDENT)) :]


def brace_at(text: str, position: int) -> int | None:
    """Where the brace the cursor is on is, either side of it."""
    for at in (position, position - 1):
        if 0 <= at < len(text) and text[at] in "{}":
            return at

    return None


def matching_brace(text: str, position: int) -> int | None:
    """The brace that closes or opens the one at `position`.

    Braces inside a string or a comment are text, not structure, so they are
    stepped over -- `print(@myself, "{")` is not an unclosed block.
    """
    opening = text[position] == "{"
    step = 1 if opening else -1
    depth = 0

    for at in range(position, len(text) if opening else -1, step):
        char = text[at]

        # The cheap test first: reading back to the start of the line to see
        # whether a character is code costs too much to do for all of them.
        if char not in "{}" or not structural(text, at):
            continue

        if char == "{":
            depth += 1 if opening else -1
        else:
            depth -= 1 if opening else -1

        if depth == 0:
            return at

    return None


def structural(text: str, position: int) -> bool:
    """Whether the character at `position` is code rather than words.

    Read from the start of its line, which is as far as a string or a line
    comment can reach; a `/* */` block is left out of it, since the braces
    people put inside one are the same braces they put inside a string.
    """
    start = text.rfind("\n", 0, position) + 1
    in_string = False
    escaped = False

    for at in range(start, position):
        char = text[at]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "/" and text[at : at + 2] == "//":
            return False

    return not in_string


def indent_columns(text: str) -> int:
    """How far `text` is indented, counting a tab out to the next stop."""
    columns = 0
    for char in text:
        if char == " ":
            columns += 1
        elif char == "\t":
            columns += len(INDENT) - columns % len(INDENT)
        else:
            break
    return columns


def neighbour_columns(block, forward: bool) -> int:
    """The indentation of the nearest line one way with anything on it."""
    while True:
        block = block.next() if forward else block.previous()
        if not block.isValid():
            return 0
        if block.text().strip():
            return indent_columns(block.text())


def guide_depth(block) -> int:
    """How many guides to draw down `block`.

    A blank line has no indentation of its own, so it borrows the deeper of
    its neighbours -- otherwise every empty line inside a block punches a hole
    through the rules running past it.
    """
    text = block.text()
    if not text.strip():
        columns = max(neighbour_columns(block, False), neighbour_columns(block, True))
    else:
        columns = indent_columns(text)

    return columns // len(INDENT)
