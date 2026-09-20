"""Autocomplete: the popup that offers what `completions` works out.

It is driven from the editor's key handling rather than from `textChanged`,
so opening a file or a failed compile moving the cursor never makes a popup
appear -- it only ever shows up under something that was just typed.

Which keys the popup itself takes is Qt's: while it is up, the editor ignores
Return, Enter, Tab and Escape, and QCompleter turns the first three into an
insertion and the last into a dismissal.
"""

# pyright: basic

from PySide6.QtCore import QModelIndex, QObject, QRect, QSize, Qt
from PySide6.QtGui import QColor, QStandardItem, QStandardItemModel, QTextCursor
from PySide6.QtWidgets import QCompleter, QStyledItemDelegate

from tfbpseudo.editor.completions import (
    KEY_CHARS,
    Completion,
    Proposal,
    completions,
    prefix_at,
)
from tfbpseudo.editor.theme import DEFAULT, Theme
from tfbpseudo.editor.widgets import CodeEditor

DETAIL = Qt.ItemDataRole.UserRole + 1
# Which proposal a row stands for: the popup filters through a proxy, so a
# row number is not one into our own list, but the roles travel with it.
WHICH = Qt.ItemDataRole.UserRole + 2

# Typing one letter matches nearly everything, and a popup that opens on every
# keystroke is in the way more often than it helps.
MIN_PREFIX = 2

# The punctuation worth looking after, on top of the letters: each one can end
# up somewhere with a closed list of what comes next -- a field after a ".", an
# enum member after the comma that starts its argument, `end` after `flow `, a
# preset after its key. Nothing opens unless that list is in fact closed, so a
# space is cheap.
TRIGGERS = (".", ":", "#", "@", ",", " ", *KEY_CHARS)

MAX_VISIBLE = 12
PADDING = 24  # room for the gap between a label and its detail


def style_sheet(theme: Theme) -> str:
    return f"""
    QListView {{
        background-color: {theme.overlay};
        color: {theme.text};
        border: 1px solid {theme.border};
        outline: none;
        padding: 2px;
    }}
    QListView::item {{ padding: 1px 4px; }}
    QListView::item:selected {{
        background-color: {theme.selection};
        color: {theme.selected_text};
    }}
    """


class ProposalDelegate(QStyledItemDelegate):
    """Draws a proposal: its label, and its detail dimmed on the right."""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)

        detail = index.data(DETAIL)
        if not detail:
            return

        painter.save()
        painter.setPen(QColor(self.theme.disabled))
        painter.drawText(
            option.rect.adjusted(0, 0, -6, 0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            detail,
        )
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        detail = index.data(DETAIL)

        if detail:
            metrics = option.fontMetrics
            size.setWidth(size.width() + metrics.horizontalAdvance(detail) + PADDING)

        return size


class Completer(QObject):
    """Autocomplete over one `CodeEditor`."""

    def __init__(self, editor: CodeEditor, theme: Theme = DEFAULT):
        super().__init__(editor)
        self.editor = editor
        self.theme = theme
        self.proposals: list[Proposal] = []

        self.model = QStandardItemModel(self)
        self.completer = QCompleter(self.model, self)
        self.completer.setWidget(editor)
        self.completer.setCompletionMode(
            QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        self.completer.activated[QModelIndex].connect(self.insert)

        popup = self.completer.popup()
        popup.setItemDelegate(ProposalDelegate(theme, popup))
        popup.setUniformItemSizes(True)

        editor.completer = self
        self.set_theme(theme)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        popup = self.completer.popup()
        popup.setItemDelegate(ProposalDelegate(theme, popup))
        popup.setStyleSheet(style_sheet(theme))

    # ----- opening and closing -----

    def popup_visible(self) -> bool:
        return self.completer.popup().isVisible()

    def hide(self) -> None:
        self.completer.popup().hide()

    def typed(self, text: str) -> None:
        """Called after a key has gone into the text.

        An open popup follows along with whatever is typed next; a closed one
        opens on an operator, or once there is enough of a name to be worth
        narrowing down.
        """
        if self.popup_visible():
            self.suggest(minimum=1)
            return

        if text and (text[-1] in TRIGGERS or text[-1].isalnum() or text[-1] == "_"):
            self.suggest(minimum=MIN_PREFIX)

    def suggest(self, minimum: int = 0, force: bool = False) -> None:
        """Show what can be written at the cursor, or hide the popup when that
        is nothing.

        `minimum` is how much has to have been typed first, which a closed
        list -- the fields of a type, the words that follow `flow` -- is
        excused from: there are few enough of those to be worth seeing before
        anything has been typed at all.
        """
        cursor = self.editor.textCursor()
        found = completions(self.editor.toPlainText(), cursor.position())
        enough = force or found.precise or len(found.prefix) >= minimum

        if not enough or not found.proposals:
            self.hide()
            return

        self.fill(found)
        self.completer.complete(self.rectangle(found.prefix))
        self.completer.popup().setCurrentIndex(self.model.index(0, 0))

    # ----- the popup -----

    def fill(self, found: Completion) -> None:
        self.proposals = found.proposals
        self.model.clear()

        for row, proposal in enumerate(self.proposals):
            item = QStandardItem(proposal.label)
            item.setData(proposal.detail, DETAIL)
            item.setData(row, WHICH)
            item.setEditable(False)
            self.model.appendRow(item)

    def rectangle(self, prefix: str) -> QRect:
        """Where to put the popup: under the start of what it would replace,
        wide enough for the longest entry it holds."""
        popup = self.completer.popup()

        rect = self.editor.cursorRect()
        rect.translate(self.editor.viewport().pos())
        rect.setLeft(
            rect.left() - self.editor.fontMetrics().horizontalAdvance(prefix)
        )

        width = popup.sizeHintForColumn(0) + popup.frameWidth() * 2
        if len(self.proposals) > MAX_VISIBLE:
            width += popup.verticalScrollBar().sizeHint().width()
        rect.setWidth(max(width, 160))

        popup.setMaximumHeight(
            MAX_VISIBLE * popup.sizeHintForRow(0) + popup.frameWidth() * 2
        )

        return rect

    def insert(self, index: QModelIndex) -> None:
        """Put the chosen proposal in, over the name it completes."""
        row = index.data(WHICH)
        if row is None or row >= len(self.proposals):
            return

        proposal = self.proposals[row]
        cursor = self.editor.textCursor()
        prefix = prefix_at(self.editor.toPlainText(), cursor.position())

        cursor.beginEditBlock()
        cursor.setPosition(
            cursor.position() - len(prefix), QTextCursor.MoveMode.KeepAnchor
        )
        cursor.insertText(proposal.text())

        if proposal.back:
            cursor.setPosition(cursor.position() - proposal.back)

        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)

    # ----- keys the popup owns -----

    TAKES = (
        Qt.Key.Key_Return,
        Qt.Key.Key_Enter,
        Qt.Key.Key_Tab,
        Qt.Key.Key_Backtab,
        Qt.Key.Key_Escape,
    )

    def takes(self, event) -> bool:
        """Whether the popup is going to deal with this key itself, in which
        case the editor has to leave it alone."""
        return self.popup_visible() and event.key() in self.TAKES
