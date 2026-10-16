"""The text widget: a plain editor with a line-number gutter.

Compile errors carry a line and a column, so the gutter earns its place --
"12:7: unknown flow control" is only useful next to line numbers.

Scripts nest a few levels deep -- prescript, behavior, flow, else -- so the
editor draws a rule down every level of indentation, keeps the indent when you
press Return, and marks the brace matching the one under the cursor. Anything
it indents is the four spaces the decompiler writes.

The line commands -- comment, indent, move, duplicate -- work on whole lines
and keep whatever was selected selected, so they can be leant on.

A block can be folded away by the arrow beside the line that opens it. What is
folded is not kept anywhere: a hidden line is the state, so an edit cannot put
the two out of step, and anything left hidden with nothing folding it is shown
again on the next change.
"""

# pyright: basic

from collections.abc import Iterable
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPointF, QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFontDatabase,
    QPainter,
    QPolygonF,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QPlainTextDocumentLayout,
    QPlainTextEdit,
    QTextEdit,
    QToolTip,
    QWidget,
)

from tfbpseudo.editor.completions import help_at
from tfbpseudo.editor.theme import DEFAULT, Theme

if TYPE_CHECKING:
    from tfbpseudo.editor.completer import Completer

DEFAULT_FONT_SIZE = 12  # points, until the settings say otherwise

INDENT = "    "  # what the decompiler writes for one level
COMMENT = "// "  # what a commented-out line starts with
FOLDED_MARK = " …"  # what stands in for the lines a fold took away


class LineNumbers(QWidget):
    """The gutter down the left of the editor: line numbers, and the fold
    arrow beside every line that opens a block."""

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor
        self.hovered: int | None = None  # the line whose arrow is under the mouse

        # For the arrow to light up under the mouse it has to hear about the
        # mouse without a button being held down.
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, event) -> None:
        self.editor.paint_gutter(event)

    def arrow_at(self, point) -> int | None:
        """The line whose fold arrow is at `point`, if one is."""
        if point.x() < self.width() - self.editor.fold_column_width():
            return None

        block = self.editor.block_at(point.y())
        if block is None or not opens_fold(block.text()):
            return None

        return block.blockNumber()

    def mousePressEvent(self, event) -> None:
        line = self.arrow_at(event.position().toPoint())

        if line is None:
            super().mousePressEvent(event)
            return

        self.editor.toggle_fold(line)

    def mouseMoveEvent(self, event) -> None:
        self.set_hovered(self.arrow_at(event.position().toPoint()))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.set_hovered(None)
        super().leaveEvent(event)

    def set_hovered(self, line: int | None) -> None:
        if line == self.hovered:
            return

        self.hovered = line
        self.setCursor(
            Qt.CursorShape.ArrowCursor
            if line is None
            else Qt.CursorShape.PointingHandCursor
        )
        self.update()


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None, theme: Theme = DEFAULT):
        super().__init__(parent)
        self.theme = theme

        self.font_size = DEFAULT_FONT_SIZE

        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.set_font_size(self.font_size)
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

        # Where every block opens and closes, worked out once per edit: the
        # gutter asks for this on every repaint, scrolling included.
        self._folds: dict[int, int] = {}
        self._folds_revision = -1
        # Whether any line might be hidden. Typing in a file with nothing
        # folded is the common case, and it should not pay for this at all.
        self._anything_folded = False

        self.blockCountChanged.connect(self.update_gutter_width)
        self.updateRequest.connect(self.update_gutter)
        self.cursorPositionChanged.connect(self.highlight_lines)
        self.textChanged.connect(self.clear_error)
        self.textChanged.connect(self.prune_folds)

        self.update_gutter_width()
        self.highlight_lines()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.highlight_lines()
        self.gutter.update()

    # ----- how big the text is -----

    def set_font_size(self, points: int) -> None:
        """Set the size of the text, and of everything measured against it:
        the indent Tab moves by, and how wide the gutter has to be."""
        self.font_size = points

        font = self.font()
        font.setPointSize(points)
        self.setFont(font)

        self.setTabStopDistance(len(INDENT) * self.fontMetrics().horizontalAdvance(" "))
        self.update_gutter_width()

    def changeEvent(self, event) -> None:
        """Keep the size that was asked for.

        Restyling the window -- which is what switching theme does, through
        the stylesheets the find box and the panel carry -- re-polishes this
        widget, and the polish puts the font back to the one it inherits. So
        the size is remembered rather than read off the widget, and set again
        whenever something has taken it away.
        """
        super().changeEvent(event)

        if (
            event.type() in (QEvent.Type.StyleChange, QEvent.Type.FontChange)
            and self.font().pointSize() != self.font_size
        ):
            self.set_font_size(self.font_size)

    # ----- the gutter -----

    def fold_column_width(self) -> int:
        """The strip of the gutter the fold arrows live in, against the text."""
        return self.fontMetrics().height()

    def gutter_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return (
            12
            + self.fontMetrics().horizontalAdvance("9") * digits
            + self.fold_column_width()
        )

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
                    self.gutter.width() - self.fold_column_width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number),
                )

                if opens_fold(block.text()):
                    self.paint_fold_arrow(painter, block.blockNumber(), top)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

    def paint_fold_arrow(self, painter: QPainter, line: int, top: float) -> None:
        """The arrow beside a line that opens a block: down while the block is
        there to read, along once it has been folded away.

        Level with the line number rather than with the line's whole box --
        the two sit side by side, so they have to agree with each other.
        """
        column = self.fold_column_width()
        folded = self.is_folded(line)

        centre = QPointF(
            self.gutter.width() - column / 2, top + self.fontMetrics().height() / 2
        )

        # Roughly as wide as it is tall, so neither way round reads as a slot.
        reach = max(3.0, column / 4)
        across, along = (reach * 0.6, reach) if folded else (reach, reach * 0.6)

        if folded:
            corners = [
                QPointF(centre.x() - across, centre.y() - along),
                QPointF(centre.x() + across * 1.2, centre.y()),
                QPointF(centre.x() - across, centre.y() + along),
            ]
        else:
            corners = [
                QPointF(centre.x() - across, centre.y() - along),
                QPointF(centre.x() + across, centre.y() - along),
                QPointF(centre.x(), centre.y() + along * 1.2),
            ]

        lit = folded or self.gutter.hovered == line
        colour = QColor(self.theme.gutter_current if lit else self.theme.gutter_text)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(colour)
        painter.drawPolygon(QPolygonF(corners))
        painter.restore()

    # ----- the rule down each level of indentation -----

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self.paint_indent_guides(event)
        self.paint_fold_marks(event)

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

    # ----- folding -----

    def folds(self) -> dict[int, int]:
        """Every line that opens a block and the line that closes it, worked
        out from the text and kept until the text changes."""
        revision = self.document().revision()

        if revision != self._folds_revision:
            self._folds = fold_regions(self.toPlainText())
            self._folds_revision = revision

        return self._folds

    def is_folded(self, line: int) -> bool:
        """Whether the block `line` opens has been folded away.

        The hidden lines are the state -- there is no list of folds to keep in
        step with the text, so an edit cannot leave the two disagreeing.
        """
        block = self.document().findBlockByNumber(line)
        if not block.isValid() or not opens_fold(block.text()):
            return False

        body = block.next()

        return body.isValid() and not body.isVisible()

    def toggle_fold(self, line: int) -> None:
        self.unfold(line) if self.is_folded(line) else self.fold(line)

    def fold(self, line: int) -> None:
        """Hide the block `line` opens, down to the line that closes it."""
        end = self.folds().get(line)
        if end is None:
            return

        document = self.document()
        for number in range(line + 1, end + 1):
            document.findBlockByNumber(number).setVisible(False)

        self._anything_folded = True

        self.leave_cursor_in_sight()
        self.folds_changed(line, end)

    def unfold(self, line: int) -> None:
        """Show everything `line` folded away, blocks folded inside it too.

        Opening the outer one opens the lot because the hidden lines are all
        there is to go on: once this fold hid them, a block that was folded
        before looks exactly like one this fold took away, and guessing wrong
        would leave text hidden with an arrow claiming it is there.
        """
        end = self.folds().get(line)
        if end is None:
            return

        document = self.document()
        for number in range(line + 1, end + 1):
            document.findBlockByNumber(number).setVisible(True)

        self.folds_changed(line, end)

    def fold_all(self, folded: bool = True) -> None:
        """Fold every block in the file, or open every one of them.

        One relayout at the end rather than one per block: the whole file is
        moving either way, and a script with a thousand blocks in it should
        not be laid out a thousand times over.
        """
        document = self.document()
        count = document.blockCount()

        # Which lines are inside a block at all -- the ranges nest, so this is
        # worked out once and then walked through in one pass.
        inside = [False] * count
        for start, end in self.folds().items():
            for number in range(start + 1, min(end, count - 1) + 1):
                inside[number] = True

        block = document.firstBlock()
        while block.isValid():
            away = folded and inside[block.blockNumber()]
            if block.isVisible() == away:
                block.setVisible(not away)
            block = block.next()

        self._anything_folded = folded

        if folded:
            self.leave_cursor_in_sight()

        self.folds_changed(0, document.blockCount() - 1)

    def leave_cursor_in_sight(self) -> None:
        """Put the cursor on the nearest line above it that can be seen.

        Folding is not editing, so it must not take the cursor anywhere
        surprising -- but a cursor left on a line that has been folded away
        would type into text nobody can see.
        """
        block = self.textCursor().block()
        if block.isVisible():
            return

        while block.isValid() and not block.isVisible():
            block = block.previous()

        if block.isValid():
            self.setTextCursor(QTextCursor(block))

    def toggle_fold_at_cursor(self) -> None:
        """Fold the block the cursor is on, or the one it is inside of."""
        folds = self.folds()
        line = self.textCursor().blockNumber()

        if line not in folds:
            line = max(
                (start for start, end in folds.items() if start < line <= end),
                default=-1,
            )

        if line >= 0:
            self.toggle_fold(line)

    def prune_folds(self) -> None:
        """Show any line left hidden with nothing folding it.

        Deleting the line that opened a block would otherwise leave its body
        hidden with no arrow to bring it back, which reads as text that has
        gone missing.
        """
        if not self._anything_folded:
            return

        document = self.document()
        count = document.blockCount()
        hidden = [False] * count

        for start, end in self.folds().items():
            body = document.findBlockByNumber(start + 1)
            if body.isValid() and not body.isVisible():
                for number in range(start + 1, min(end, count - 1) + 1):
                    hidden[number] = True

        shown = False
        left = False
        for number in range(count):
            block = document.findBlockByNumber(number)
            if block.isVisible():
                continue

            if hidden[number]:
                left = True
            else:
                block.setVisible(True)
                shown = True

        self._anything_folded = left

        if shown:
            self.folds_changed(0, count - 1)

    def folds_changed(self, first: int, last: int) -> None:
        """Lay the document out again over the lines that came or went."""
        document = self.document()
        start = document.findBlockByNumber(first)
        end = document.findBlockByNumber(last)

        if start.isValid() and end.isValid():
            document.markContentsDirty(
                start.position(), end.position() + end.length() - start.position()
            )

        layout = document.documentLayout()
        if isinstance(layout, QPlainTextDocumentLayout):
            # What tells the widget its content is a different height now, so
            # the scrollbar and the first visible block are worked out again.
            layout.requestUpdate()

        self.viewport().update()
        self.gutter.update()

    def reveal_block(self, block) -> None:
        """Open whatever folds are hiding `block`.

        Every jump to a line ends up here -- find, go to definition, the jump
        to a failed compile -- because landing the cursor on a line that has
        been folded away would leave it typing somewhere invisible.
        """
        if not block.isValid() or block.isVisible():
            return

        number = block.blockNumber()
        holders = sorted(
            start for start, end in self.folds().items() if start < number <= end
        )

        # Outermost first: opening one block opens what is inside it, so the
        # first of these is usually the only one left to do.
        for start in holders:
            if self.is_folded(start):
                self.unfold(start)

    def reveal_position(self, position: int) -> None:
        """The same for wherever `position` is in the text."""
        self.reveal_block(self.document().findBlock(position))

    def block_at(self, y: int):
        """The block drawn at `y` in the viewport, or None above or below the
        text. Folded-away blocks take up no height, so they are never hit."""
        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()

        while block.isValid():
            bottom = top + self.blockBoundingRect(block).height()

            if block.isVisible() and top <= y < bottom:
                return block

            block = block.next()
            top = bottom

        return None

    def paint_fold_marks(self, event) -> None:
        """A mark after a folded line, so it does not read as a line that
        simply ends there."""
        if not self._anything_folded:
            return

        painter = QPainter(self.viewport())
        painter.setPen(QColor(self.theme.disabled))

        margin = self.document().documentMargin()
        metrics = self.fontMetrics()
        offset = self.contentOffset()

        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(offset).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if (
                block.isVisible()
                and bottom >= event.rect().top()
                and self.is_folded(block.blockNumber())
            ):
                left = self.blockBoundingGeometry(block).translated(offset).left()
                painter.drawText(
                    int(left + margin + metrics.horizontalAdvance(block.text())),
                    int(top) + metrics.ascent(),
                    FOLDED_MARK,
                )

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

        self.reveal_block(block)

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


def opens_fold(line: str) -> bool:
    """Whether `line` opens a block: the last thing on it, its comment aside,
    is the brace that opens one.

    The gutter asks this of every line it draws, on every repaint, which is
    why it is a line at a time and not a look into `fold_regions` -- reading
    the whole script to put an arrow beside forty lines is what makes typing
    in a long one feel slow. A line that opens and closes a block ends with
    the closing brace, so it says no, which is the right answer: there is
    nothing in between to fold away.
    """
    return code_of(line).rstrip().endswith("{")


def code_of(line: str) -> str:
    """`line` up to the `//` that comments the rest of it out, if any. A `//`
    inside a string is text, not the start of a comment."""
    in_string = False
    escaped = False

    for at, char in enumerate(line):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "/" and line.startswith("//", at):
            return line[:at]

    return line


def fold_regions(text: str) -> dict[int, int]:
    """Every block that can be folded: the line that opens it and the line
    whose brace closes it, both 0-based.

    One pass with a stack, because the gutter wants every block in the file on
    each repaint and asking `matching_brace` per line would read the text once
    per block. Only the lines with a brace on them are read character by
    character -- neither a string nor a `//` comment can cross a line, so a
    line with no brace cannot change what the next one means. Braces are read
    the way `matching_brace` reads them, so what folds and what the cursor
    matches cannot disagree.

    A block that opens and closes on one line is left out: there is nothing
    between the braces to take away.
    """
    regions: dict[int, int] = {}
    opened: list[int] = []

    for line, written in enumerate(text.split("\n")):
        if "{" not in written and "}" not in written:
            continue

        in_string = False
        escaped = False

        for at, char in enumerate(written):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "/" and written.startswith("//", at):
                break  # the rest of the line is a comment
            elif char == "{":
                opened.append(line)
            elif char == "}" and opened:
                start = opened.pop()
                if line > start:
                    regions[start] = line

    return regions


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
