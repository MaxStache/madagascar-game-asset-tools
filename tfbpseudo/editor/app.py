"""A text editor for TfbPseudo.

Open a compiled `.ai` and it is decompiled into the editor; open a `.tai` and
it is read as it is. From there, save the text back out as `.tai` or compile it
to a `.ai`. Compiling never touches the file you opened -- it asks where to put
the result -- so a decompile-edit-compile round never overwrites the original
by accident.
"""

# pyright: basic

import os
import signal
import traceback
from pathlib import Path
from typing import cast

from tfbpseudo.compiler import METHOD_OPCODE_TABLE, compile_source
from tfbpseudo.decompiler import decompile_script
from tfbpseudo.errors import CompileError, DecompileError, ParseError
from tfbscript.ansi import set_colors_enabled
from tfbscript.script import ScriptFile

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import (
        QAction,
        QActionGroup,
        QFont,
        QFontDatabase,
        QKeySequence,
        QTextCursor,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QLabel,
        QMainWindow,
        QMessageBox,
        QSplitter,
        QStyleFactory,
    )
except ModuleNotFoundError:  # pragma: no cover - the editor just cannot run
    print("WARN: PySide6 not installed, the editor wont work")

from tfbscript.editor.fonts import register_bold_variant

from . import settings
from .completer import Completer
from .completions import call_at, definition_of, name_at
from .highlighter import TfbPseudoHighlighter
from .panel import HEIGHT as PANEL_HEIGHT, Panel, describe
from .search import SearchBox
from .theme import DEFAULT, THEMES, Theme, qt_palette, scrollbar_style
from .widgets import CodeEditor

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

signal.signal(signal.SIGINT, signal.SIG_DFL)

# The decompiler renders through tfbscript, which colours for a terminal.
set_colors_enabled(False)

SCRIPT_SUFFIX = ".ai"
SOURCE_SUFFIX = ".tai"

OPEN_FILTER = (
    f"TFB scripts (*{SCRIPT_SUFFIX} *{SOURCE_SUFFIX});;"
    f"Compiled script (*{SCRIPT_SUFFIX});;"
    f"TfbPseudo source (*{SOURCE_SUFFIX});;"
    "All files (*)"
)


# What a new file starts as: the shape of a script with nothing in it, laid
# out the way the decompiler lays one out, so an empty editor says what goes
# where. It compiles as it stands -- every block here is allowed to be empty,
# and the notes sit outside the declaration blocks because only a declaration
# can go inside one.
STARTER = """\
// A new script. Fill in the blocks you need and delete the rest.

// Variables the level already owns, spelled the way it spells them:
//     "players::set::actor";
globals {
}

// This script's own. A `user` one has to be made with createVariable before
// anything reads it:
//     "my timer::user::value";
locals {
}

prescript {
    startup {
        // Runs once, as the script starts.
    }

    shutdown {
        // Runs once, as the script stops.
    }

    update {
        // Runs every frame, whichever behavior is the current one.
    }
}

// A behavior is a body that runs while it is the current one; setBehavior
// switches to another.
behavior Idle {
}
"""


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.source_path: Path | None = None  # the .tai this text is saved as
        self.opened_from: Path | None = None  # what was opened, whichever kind

        self.theme = DEFAULT

        self.editor = CodeEditor(theme=self.theme)
        self.highlighter = TfbPseudoHighlighter(self.editor.document(), self.theme)
        self.search = SearchBox(self.editor, self.theme)
        self.completer = Completer(self.editor, self.theme)
        self.panel = Panel(self.editor, self.theme)

        # The panel keeps the height it is dragged to while the window grows,
        # and the editor cannot be collapsed out of the way by accident.
        self.split = QSplitter(Qt.Orientation.Vertical)
        self.split.addWidget(self.editor)
        self.split.addWidget(self.panel)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 0)
        self.split.setCollapsible(0, False)
        self.setCentralWidget(self.split)

        self.editor.document().modificationChanged.connect(self.update_title)

        # What the call under the cursor takes, out of the way of the
        # messages the status bar shows on the left.
        self.signature = QLabel("")
        self.statusBar().addPermanentWidget(self.signature)
        self.editor.cursorPositionChanged.connect(self.update_signature)

        self.build_menus()
        self.resize(1000, 760)
        self.split.setSizes([760 - PANEL_HEIGHT, PANEL_HEIGHT])
        self.start_empty()
        self.status("Open a .ai to decompile it, or a .tai to edit it.")
        self.update_title()

    # ----- chrome -----

    def build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")

        self.add_action(
            file_menu, "New", QKeySequence.StandardKey.New, self.new_file
        )
        self.add_action(
            file_menu, "Open...", QKeySequence.StandardKey.Open, self.open_file
        )
        self.recent_menu = file_menu.addMenu("Open Recent")
        self.fill_recent_menu()
        file_menu.addSeparator()
        self.add_action(
            file_menu, "Save", QKeySequence.StandardKey.Save, self.save_source
        )
        self.add_action(
            file_menu,
            "Save As...",
            QKeySequence.StandardKey.SaveAs,
            self.save_source_as,
        )
        file_menu.addSeparator()
        self.add_action(
            file_menu,
            "Compile to .ai",
            QKeySequence("Ctrl+B"),
            self.compile_to_script,
        )
        self.add_action(
            file_menu,
            "Compile As...",
            QKeySequence("Ctrl+Shift+B"),
            self.compile_as,
        )
        file_menu.addSeparator()
        self.add_action(
            file_menu, "Quit", QKeySequence.StandardKey.Quit, self.close
        )

        edit_menu = self.menuBar().addMenu("Edit")
        self.add_action(
            edit_menu,
            "Complete",
            QKeySequence("Ctrl+Space"),
            lambda: self.completer.suggest(force=True),
        )
        edit_menu.addSeparator()
        self.add_action(
            edit_menu,
            "Toggle Comment",
            QKeySequence("Ctrl+/"),
            self.editor.toggle_comment,
        )
        self.add_action(
            edit_menu,
            "Duplicate Line",
            QKeySequence("Ctrl+D"),
            self.editor.duplicate_lines,
        )
        self.add_action(
            edit_menu,
            "Move Line Up",
            QKeySequence("Alt+Up"),
            lambda: self.editor.move_lines(down=False),
        )
        self.add_action(
            edit_menu,
            "Move Line Down",
            QKeySequence("Alt+Down"),
            lambda: self.editor.move_lines(down=True),
        )
        edit_menu.addSeparator()
        self.add_action(
            edit_menu,
            "Go to Definition",
            QKeySequence("F12"),
            self.go_to_definition,
        )
        edit_menu.addSeparator()
        self.add_action(
            edit_menu,
            "Find...",
            QKeySequence.StandardKey.Find,
            self.search.activate,
        )
        self.add_action(
            edit_menu,
            "Find Next",
            QKeySequence.StandardKey.FindNext,
            self.search.next_match,
        )
        self.add_action(
            edit_menu,
            "Find Previous",
            QKeySequence.StandardKey.FindPrevious,
            self.search.previous_match,
        )

        script_menu = self.menuBar().addMenu("Script")
        self.add_action(
            script_menu, "Check", QKeySequence("Ctrl+K"), self.check_source
        )

        view_menu = self.menuBar().addMenu("View")
        themes = QActionGroup(view_menu)
        themes.setExclusive(True)

        for name, theme in THEMES.items():
            action = QAction(name, view_menu)
            action.setCheckable(True)
            action.setChecked(theme is self.theme)
            action.triggered.connect(lambda _, t=theme: self.apply_theme(t))
            themes.addAction(action)
            view_menu.addAction(action)

    def apply_theme(self, theme: Theme) -> None:
        """Repaint everything -- the chrome and the syntax have to move
        together or one of them ends up unreadable."""
        self.theme = theme

        app = cast(QApplication, QApplication.instance())
        if app is not None:
            app.setPalette(qt_palette(theme))
            app.setStyleSheet(scrollbar_style(theme))

        self.editor.set_theme(theme)
        self.highlighter.set_theme(theme)
        self.search.set_theme(theme)
        self.completer.set_theme(theme)
        self.panel.set_theme(theme)

    def fill_recent_menu(self) -> None:
        """The files opened lately, newest first, under File."""
        self.recent_menu.clear()
        paths = settings.recent()

        for path in paths:
            where = Path(path)
            action = QAction(f"{where.name}  --  {where.parent}", self.recent_menu)
            action.triggered.connect(lambda _, at=path: self.load(at))
            self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()

        if paths:
            clear = QAction("Clear", self.recent_menu)
            clear.triggered.connect(self.clear_recent)
            self.recent_menu.addAction(clear)
        else:
            nothing = QAction("Nothing opened yet", self.recent_menu)
            nothing.setEnabled(False)
            self.recent_menu.addAction(nothing)

    def clear_recent(self) -> None:
        settings.forget_recent()
        self.fill_recent_menu()

    def add_action(self, menu, title: str, shortcut, handler) -> None:
        action = QAction(title, menu)
        action.setShortcut(shortcut)
        action.triggered.connect(handler)
        menu.addAction(action)

    def status(self, message: str) -> None:
        self.statusBar().showMessage(message)
        self.panel.log(message)

    def document_name(self) -> str:
        """What to call what is being edited, saved or not."""
        return self.source_path.name if self.source_path else "untitled"

    def update_title(self) -> None:
        dirty = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"{dirty}{self.document_name()} - TfbPseudo Editor")

    # ----- opening -----

    def start_empty(self) -> None:
        """Start on the empty layout rather than on nothing at all.

        It is text like any other, not a file: nothing has been opened, so it
        counts as unmodified and Save still asks where to put it.
        """
        self.editor.setPlainText(STARTER)
        self.editor.document().setModified(False)
        self.panel.lint()  # the panel is about this text, not the last lot

        # The cursor goes where a script usually starts being written.
        found = self.editor.document().find("startup {")
        if not found.isNull():
            found.movePosition(QTextCursor.MoveOperation.Down)
            found.movePosition(QTextCursor.MoveOperation.EndOfLine)
            self.editor.setTextCursor(found)

    def new_file(self) -> None:
        """Back to the empty layout, with no file behind it."""
        if not self.confirm_discard("Save the source before starting a new one?"):
            return

        self.source_path = None
        self.opened_from = None
        self.start_empty()
        self.update_title()
        self.status("A new script.")

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open script", str(Path.cwd()), OPEN_FILTER
        )
        if path:
            self.load(Path(path))

    def load(self, path: Path | str) -> None:
        """Read `path`, decompiling it first when it is a compiled script."""
        path = Path(path)

        script = None

        try:
            if path.suffix.lower() == SCRIPT_SUFFIX:
                script = ScriptFile.from_path(path)
                text = decompile_script(script)
                # The text is a decompilation, not a file on disk yet, so Save
                # has to ask where to put it rather than overwrite the .ai.
                self.source_path = None
                note = f"Decompiled {path.name}"
            else:
                text = path.read_text()
                self.source_path = path
                note = f"Opened {path.name}"
        except Exception as error:
            self.report(f"Could not open {path.name}", error)
            return

        self.opened_from = path
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        self.panel.lint()
        self.update_title()
        self.status(f"{note} -- {len(text.splitlines())} lines")

        settings.remember_opened(path)
        self.fill_recent_menu()

        if script is not None:
            self.panel.report(
                f"Decompiled {path.name}",
                [
                    f"read {path.stat().st_size} bytes of {path.name}",
                    *describe(script),
                    f"written out as {len(text.splitlines())} lines of TfbPseudo",
                ],
            )

    # ----- saving the text -----

    def save_source(self) -> bool:
        if self.source_path is None:
            return self.save_source_as()

        return self.write_source(self.source_path)

    def save_source_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save TfbPseudo source",
            str(self.suggested_path(SOURCE_SUFFIX)),
            f"TfbPseudo source (*{SOURCE_SUFFIX});;All files (*)",
        )
        if not path:
            return False

        return self.write_source(Path(path))

    def write_source(self, path: Path) -> bool:
        try:
            path.write_text(self.editor.toPlainText())
        except OSError as error:
            self.report(f"Could not write {path.name}", error)
            return False

        self.source_path = path
        self.editor.document().setModified(False)
        self.update_title()
        self.status(f"Saved {path}")
        return True

    # ----- compiling -----

    def check_source(self) -> None:
        """Compile without writing anything, just to see if it holds up."""
        self.panel.lint()  # no waiting for the debounce when it was asked for
        script = self.compile_text()
        if script is None:
            return

        instructions = sum(op.total_span() for op in script.instructions)
        self.status(
            f"Compiles: {instructions} instructions, "
            f"{len(script.opcode_table.entries)} opcodes, "
            f"{len(script.global_refs.entries)} globals, "
            f"{len(script.local_refs.entries)} locals"
        )
        self.panel.report(f"Checked {self.document_name()}", describe(script))

    def build_key(self) -> Path | None:
        """What a remembered build target is remembered against: the file this
        text came from, saved as or decompiled from."""
        return self.source_path or self.opened_from

    def compile_to_script(self) -> None:
        """Compile to wherever this source went last time.

        The first build of a source asks, and only what was chosen in that
        dialog is remembered -- opening a shipped .ai never makes it the thing
        the next Ctrl+B overwrites.
        """
        target = settings.build_target(self.build_key())
        if target is None:
            self.compile_as()
            return

        self.build(target)

    def compile_as(self) -> None:
        """Compile somewhere chosen now, and build there from then on."""
        target = settings.build_target(self.build_key())

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Compile to script",
            str(target or self.suggested_path(SCRIPT_SUFFIX)),
            f"Compiled script (*{SCRIPT_SUFFIX});;All files (*)",
        )
        if path:
            self.build(Path(path))

    def build(self, target: Path) -> None:
        script = self.compile_text()
        if script is None:
            return

        try:
            with target.open("wb") as f:
                script.write(f)
        except OSError as error:
            self.report(f"Could not write {target.name}", error)
            return

        settings.remember_build(self.build_key(), target)

        self.status(f"Compiled to {target}")
        self.panel.report(
            f"Compiled {self.document_name()}",
            [
                *describe(script),
                f"written to {target}",
            ],
        )

    def compile_text(self):
        """Compile what is in the editor, pointing at the offending line when
        it does not. Returns the ScriptFile, or None."""
        self.editor.clear_error()

        try:
            return compile_source(self.editor.toPlainText())
        except (ParseError, CompileError) as error:
            self.editor.show_error_at(error.line, error.col)
            self.status(str(error))
            QMessageBox.warning(self, "Cannot compile", str(error))
        except DecompileError as error:
            self.status(str(error))
            QMessageBox.warning(self, "Cannot compile", str(error))
        except SyntaxError as error:
            # The lexer raises this for a character it cannot read.
            self.status(str(error))
            QMessageBox.warning(self, "Cannot compile", str(error))
        except Exception as error:
            self.report("Cannot compile", error)

        return None

    # ----- what the cursor is standing in -----

    def update_signature(self) -> None:
        """The call the cursor is inside, with the argument it is on in bold.

        The popup only shows while a name is being typed; this stays up for
        as long as the cursor is between the brackets, which is when the
        question "what goes here again?" actually comes up.
        """
        call = call_at(self.editor.toPlainText(), self.editor.textCursor().position())
        spec = METHOD_OPCODE_TABLE.get(call[0]) if call else None

        if call is None or spec is None:
            self.signature.clear()
            return

        method, index = call
        arguments = [
            f"[{argument.name}]" if argument.optional else argument.name
            for argument in spec.arguments
        ]
        marked = [
            f"<b>{name}</b>" if at == index else name
            for at, name in enumerate(arguments)
        ]
        self.signature.setText(f"{method}({', '.join(marked)})")

    def go_to_definition(self) -> None:
        """Jump to where the name under the cursor is declared."""
        source = self.editor.toPlainText()
        name = name_at(source, self.editor.textCursor().position())

        if not name:
            self.status("No name under the cursor.")
            return

        line = definition_of(source, name)
        if line is None:
            self.status(f"Nothing declares {name}.")
            return

        self.editor.go_to_line(line)
        self.status(f"{name} is declared on line {line}.")

    # ----- odds and ends -----

    def suggested_path(self, suffix: str) -> Path:
        base = self.source_path or self.opened_from
        if base is None:
            return Path.cwd() / f"untitled{suffix}"

        return base.with_suffix(suffix)

    def report(self, title: str, error: Exception) -> None:
        self.status(f"{title}: {error}")
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Critical)
        message.setWindowTitle(title)
        message.setText(f"{type(error).__name__}: {error}")
        message.setDetailedText("".join(traceback.format_exception(error)))
        message.exec()

    def confirm_discard(self, question: str) -> bool:
        """Whether to go ahead and lose what is in the editor.

        Saving counts as going ahead only if the save itself worked -- a
        cancelled Save As has to leave the text where it is.
        """
        if not self.editor.document().isModified():
            return True

        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            question,
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )

        if answer == QMessageBox.StandardButton.Save:
            return self.save_source()

        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event) -> None:
        if self.confirm_discard("Save the source before closing?"):
            event.accept()
        else:
            event.ignore()


def build_application(theme: Theme = DEFAULT) -> "QApplication":
    """The QApplication, in `theme`."""
    app = cast(QApplication, QApplication.instance()) or QApplication([])

    app.setStyle(QStyleFactory.create("Fusion"))
    app.setPalette(qt_palette(theme))
    app.setStyleSheet(scrollbar_style(theme))

    fonts = Path(__file__).resolve().parent.parent.parent / "tfbscript" / "editor" / "fonts"
    if fonts.exists():
        QFontDatabase.addApplicationFont(
            str(fonts / "ms-sans-serif" / "MS Sans Serif.ttf")
        )
        register_bold_variant(
            "MS Sans Serif", fonts / "ms-sans-serif-bold" / "MS Sans Serif Bold.ttf"
        )

        font = QFont("MS Sans Serif")
        font.setPixelSize(13)
        font.setBold(True)
        app.setFont(font)

    return app


def open_editor(path: Path | str | None = None) -> None:
    """Open the editor, on `path` when one is given."""
    app = build_application()

    window = EditorWindow()
    if path is not None:
        window.load(Path(path))

    window.show()
    app.exec()


def main() -> None:
    import sys

    open_editor(sys.argv[1] if len(sys.argv) > 1 else None)


if __name__ == "__main__":
    main()
