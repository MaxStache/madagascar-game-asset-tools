"""Find-in-text: a small box that floats in the top-right corner of the editor.

It sits over the text instead of taking a bar of its own so that opening it
never shifts the lines underneath -- when a failed compile has just put the
cursor on line 147, having the text jump by a row is exactly the wrong thing.
"""

# pyright: basic

from PySide6.QtCore import QEvent, QRegularExpression, Qt
from PySide6.QtGui import (
    QColor,
    QKeySequence,
    QShortcut,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QToolButton,
    QWidget,
)

from tfbpseudo.editor.theme import DEFAULT, Theme
from tfbpseudo.editor.widgets import CodeEditor

MARGIN = 8  # the gap between the box and the edge of the text area

# A one-letter query in a long script matches thousands of times, and every
# match is an extra selection Qt has to lay out. Past this many the count is
# still honest, only the tinting stops.
MAX_HIGHLIGHTS = 2000


def style_sheet(theme: Theme) -> str:
    return f"""
    QWidget#searchBox {{
        background-color: {theme.overlay};
        border: 1px solid {theme.border};
        border-radius: 3px;
    }}
    QLineEdit {{
        background-color: {theme.base};
        color: {theme.text};
        border: 1px solid {theme.border};
        border-radius: 2px;
        padding: 2px 4px;
        selection-background-color: {theme.selection};
        selection-color: {theme.selected_text};
    }}
    QLineEdit[badPattern="true"] {{
        color: {theme.unknown_method};
        border-color: {theme.unknown_method};
    }}
    QToolButton {{
        background: transparent;
        color: {theme.text};
        border: 1px solid transparent;
        border-radius: 2px;
        padding: 1px 4px;
    }}
    QToolButton:hover {{ border-color: {theme.border}; }}
    QToolButton:checked {{
        background-color: {theme.selection};
        color: {theme.selected_text};
        border-color: {theme.border};
    }}
    QToolButton:disabled {{ color: {theme.disabled}; }}
    QLabel {{ background: transparent; color: {theme.disabled}; }}
    """


class SearchBox(QWidget):
    """Incremental find over one `CodeEditor`.

    Matches are drawn as extra selections rather than by selecting text, so
    every hit stays visible at once and the current one still reads as current.
    """

    def __init__(self, editor: CodeEditor, theme: Theme = DEFAULT):
        super().__init__(editor)
        self.editor = editor
        self.theme = theme

        self.matches: list[tuple[int, int]] = []
        self.current = -1

        self.setObjectName("searchBox")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText("Find")
        self.edit.setFixedWidth(180)

        self.case_button = self.toggle("Aa", "Match case")
        self.word_button = self.toggle("W", "Whole words only")
        self.regex_button = self.toggle(".*", "Regular expression")

        self.status = QLabel("", self)
        self.status.setMinimumWidth(72)
        self.status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.prev_button = self.button("Prev", "Previous match (Shift+Enter)")
        self.next_button = self.button("Next", "Next match (Enter)")
        self.close_button = self.button("Close", "Close (Esc)")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)
        layout.addWidget(self.edit)
        layout.addWidget(self.case_button)
        layout.addWidget(self.word_button)
        layout.addWidget(self.regex_button)
        layout.addWidget(self.status)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.close_button)

        self.edit.textChanged.connect(self.refresh)
        for toggle in (self.case_button, self.word_button, self.regex_button):
            toggle.toggled.connect(self.refresh)
        self.prev_button.clicked.connect(self.previous_match)
        self.next_button.clicked.connect(self.next_match)
        self.close_button.clicked.connect(self.dismiss)

        self.shortcut(QKeySequence(Qt.Key.Key_Escape), self.dismiss)

        # Enter in the find box steps through the matches, and that is all it
        # does: a QLineEdit hands the key on to its parent when it is done with
        # it, and this box's parent is the editor, which would answer by
        # putting a newline in the script. So the key is taken here (see
        # eventFilter) rather than bound to `returnPressed`.
        self.edit.installEventFilter(self)

        # An edit invalidates the positions we found, so re-run the query.
        self.editor.document().contentsChanged.connect(self.on_document_changed)

        # The box is a child of the editor, so it has to be moved by hand
        # whenever the text area changes shape -- including when the gutter
        # widens and pushes the viewport across.
        self.editor.installEventFilter(self)
        self.editor.viewport().installEventFilter(self)

        self.set_theme(theme)
        self.hide()

    # ----- building -----

    def button(self, text: str, tip: str) -> QToolButton:
        widget = QToolButton(self)
        widget.setText(text)
        widget.setToolTip(tip)
        widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return widget

    def toggle(self, text: str, tip: str) -> QToolButton:
        widget = self.button(text, tip)
        widget.setCheckable(True)
        return widget

    def shortcut(self, sequence: QKeySequence, handler) -> None:
        action = QShortcut(sequence, self)
        action.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        action.activated.connect(handler)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.apply_style()
        self.paint_matches()

    def apply_style(self) -> None:
        self.setStyleSheet(style_sheet(self.theme))

    # ----- opening and closing -----

    def activate(self) -> None:
        """Show the box, seeded with whatever is selected in the editor."""
        selected = self.editor.textCursor().selectedText()
        if selected and " " not in selected:  # Qt's paragraph separator
            self.edit.setText(selected)

        self.show()
        self.raise_()
        self.reposition()
        self.edit.setFocus()
        self.edit.selectAll()
        self.refresh()

    def dismiss(self) -> None:
        """Hide the box and hand the editor back the focus, with the match the
        search landed on selected so it can be typed over."""
        span = self.span()
        self.editor.set_search_selections([])
        self.matches = []
        self.current = -1
        self.hide()

        if span is not None:
            self.editor.reveal_position(span[0])

            cursor = self.editor.textCursor()
            cursor.setPosition(span[0])
            cursor.setPosition(span[1], QTextCursor.MoveMode.KeepAnchor)
            self.editor.setTextCursor(cursor)

        self.editor.setFocus()

    def span(self) -> tuple[int, int] | None:
        if 0 <= self.current < len(self.matches):
            return self.matches[self.current]
        return None

    # ----- finding -----

    def find_flags(self) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if self.case_button.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.word_button.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags

    def needle(self, query: str) -> str | QRegularExpression | None:
        """What to hand `QTextDocument.find`, or None for a broken pattern."""
        if not self.regex_button.isChecked():
            return query

        expression = QRegularExpression(query)
        return expression if expression.isValid() else None

    def scan(self, query: str) -> list[tuple[int, int]]:
        document = self.editor.document()
        needle = self.needle(query)
        if needle is None:
            return []

        flags = self.find_flags()
        matches: list[tuple[int, int]] = []
        position = 0

        while True:
            cursor = document.find(needle, position, flags)
            if cursor.isNull():
                return matches

            start, end = cursor.selectionStart(), cursor.selectionEnd()
            if end == start:
                # A zero-width match, e.g. the regex "^". Stepping to `end`
                # would find it again forever, so step past it instead.
                position = start + 1
                if position >= document.characterCount():
                    return matches
                continue

            matches.append((start, end))
            position = end

    def refresh(self) -> None:
        """Re-run the query because the find box asked for it."""
        # Takes no arguments on purpose: it is connected to signals that carry
        # one (the new text, the new checked state), and Qt drops the extras.
        self.run_query(from_editor=False)

    def on_document_changed(self) -> None:
        if self.isVisible():
            self.run_query(from_editor=True)

    def run_query(self, from_editor: bool) -> None:
        """Scan for the current query and repaint the hits.

        `from_editor` marks a re-scan the editor forced by changing the text
        rather than one the find box asked for. Someone typing into the script
        is not searching, so their cursor is left exactly where they put it --
        moving it back to the last hit is how find turns into a nuisance.
        """
        query = self.edit.text()
        anchor = self.editor.textCursor().selectionStart()
        keep = None if from_editor else self.span()

        broken = bool(query) and self.needle(query) is None
        self.mark_pattern(broken)

        self.matches = self.scan(query) if query else []

        if keep is not None and keep in self.matches:
            # Widening a query that still matches here should not jump away.
            self.current = self.matches.index(keep)
        else:
            self.current = self.index_at_or_after(anchor)

        self.paint_matches()
        if not from_editor:
            self.reveal()
        self.update_status(broken)

    def index_at_or_after(self, position: int) -> int:
        for index, (start, _) in enumerate(self.matches):
            if start >= position:
                return index
        return 0 if self.matches else -1

    def next_match(self) -> None:
        self.step(1)

    def previous_match(self) -> None:
        self.step(-1)

    def step(self, delta: int) -> None:
        if not self.isVisible():
            # Find Next off the menu with the box closed. Reopen it on the
            # last query -- doing nothing at all just looks broken.
            self.activate()

        if not self.matches:
            return

        self.current = (self.current + delta) % len(self.matches)
        self.paint_matches()
        self.reveal()
        self.update_status(False)

    # ----- showing the hits -----

    def paint_matches(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []
        match = QColor(self.theme.match)
        current = QColor(self.theme.current_match)

        shown = set(range(min(len(self.matches), MAX_HIGHLIGHTS)))
        if self.current >= 0:
            shown.add(self.current)  # always tint the one being looked at

        for index in sorted(shown):
            start, end = self.matches[index]
            cursor = QTextCursor(self.editor.document())
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(
                current if index == self.current else match
            )
            selection.cursor = cursor
            selections.append(selection)

        self.editor.set_search_selections(selections)

    def reveal(self) -> None:
        """Put the cursor on the current match so the editor scrolls to it.

        The cursor is moved without selecting: the match is already tinted, and
        a selection on top of the tint would hide which hit is the current one.
        """
        span = self.span()
        if span is None:
            return

        # A hit can be inside a block that has been folded away, and the
        # point of going to it is to see it.
        self.editor.reveal_position(span[0])

        cursor = self.editor.textCursor()
        cursor.setPosition(span[0])
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()

    def update_status(self, broken: bool) -> None:
        if broken:
            self.status.setText("bad pattern")
        elif not self.edit.text():
            self.status.setText("")
        elif not self.matches:
            self.status.setText("no results")
        else:
            self.status.setText(f"{self.current + 1} of {len(self.matches)}")

        has_matches = bool(self.matches)
        self.prev_button.setEnabled(has_matches)
        self.next_button.setEnabled(has_matches)

    def mark_pattern(self, broken: bool) -> None:
        if self.edit.property("badPattern") == broken:
            return

        self.edit.setProperty("badPattern", broken)
        self.edit.style().unpolish(self.edit)
        self.edit.style().polish(self.edit)

    # ----- staying in the corner -----

    def reposition(self) -> None:
        viewport = self.editor.viewport().geometry()
        self.adjustSize()
        self.move(
            # Clamped, so a narrow window slides it off the right edge rather
            # than back behind the gutter.
            max(viewport.left(), viewport.right() - self.width() - MARGIN + 1),
            viewport.top() + MARGIN,
        )

    def eventFilter(self, watched, event) -> bool:
        if watched is self.edit and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.previous_match()
                else:
                    self.next_match()

                return True  # never let it through to the text underneath

        if event.type() == QEvent.Type.Resize and self.isVisible():
            self.reposition()

        return super().eventFilter(watched, event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # A stylesheet set while the box is hidden does not take -- Qt keeps
        # the rules it last polished with. The theme is almost always switched
        # with the box closed, so put the colours back on the way in.
        self.apply_style()
        self.reposition()
