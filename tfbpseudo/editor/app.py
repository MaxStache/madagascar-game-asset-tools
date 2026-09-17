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

from tfbpseudo.compiler import compile_source
from tfbpseudo.decompiler import decompile_script
from tfbpseudo.errors import CompileError, DecompileError, ParseError
from tfbscript.ansi import set_colors_enabled
from tfbscript.script import ScriptFile

try:
    from PySide6.QtGui import (
        QAction,
        QActionGroup,
        QFont,
        QFontDatabase,
        QKeySequence,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QMainWindow,
        QMessageBox,
        QStyleFactory,
    )
except ModuleNotFoundError:  # pragma: no cover - the editor just cannot run
    print("WARN: PySide6 not installed, the editor wont work")

from tfbscript.editor.fonts import register_bold_variant

from .highlighter import TfbPseudoHighlighter
from .theme import DEFAULT, THEMES, Theme, qt_palette
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


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.source_path: Path | None = None  # the .tai this text is saved as
        self.opened_from: Path | None = None  # what was opened, whichever kind

        self.theme = DEFAULT

        self.editor = CodeEditor(theme=self.theme)
        self.highlighter = TfbPseudoHighlighter(self.editor.document(), self.theme)
        self.setCentralWidget(self.editor)

        self.editor.document().modificationChanged.connect(self.update_title)

        self.build_menus()
        self.resize(1000, 760)
        self.status("Open a .ai to decompile it, or a .tai to edit it.")
        self.update_title()

    # ----- chrome -----

    def build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")

        self.add_action(
            file_menu, "Open...", QKeySequence.StandardKey.Open, self.open_file
        )
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
            "Compile to .ai...",
            QKeySequence("Ctrl+B"),
            self.compile_to_script,
        )
        file_menu.addSeparator()
        self.add_action(
            file_menu, "Quit", QKeySequence.StandardKey.Quit, self.close
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

        self.editor.set_theme(theme)
        self.highlighter.set_theme(theme)

    def add_action(self, menu, title: str, shortcut, handler) -> None:
        action = QAction(title, menu)
        action.setShortcut(shortcut)
        action.triggered.connect(handler)
        menu.addAction(action)

    def status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def update_title(self) -> None:
        name = self.source_path.name if self.source_path else "untitled"
        dirty = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"{dirty}{name} - TfbPseudo Editor")

    # ----- opening -----

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open script", str(Path.cwd()), OPEN_FILTER
        )
        if path:
            self.load(Path(path))

    def load(self, path: Path | str) -> None:
        """Read `path`, decompiling it first when it is a compiled script."""
        path = Path(path)

        try:
            if path.suffix.lower() == SCRIPT_SUFFIX:
                text = decompile_script(ScriptFile.from_path(path))
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
        self.update_title()
        self.status(f"{note} -- {len(text.splitlines())} lines")

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

    def compile_to_script(self) -> None:
        script = self.compile_text()
        if script is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Compile to script",
            str(self.suggested_path(SCRIPT_SUFFIX)),
            f"Compiled script (*{SCRIPT_SUFFIX});;All files (*)",
        )
        if not path:
            return

        try:
            with open(path, "wb") as f:
                script.write(f)
        except OSError as error:
            self.report(f"Could not write {Path(path).name}", error)
            return

        self.status(f"Compiled to {path}")

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

    def closeEvent(self, event) -> None:
        if not self.editor.document().isModified():
            event.accept()
            return

        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save the source before closing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )

        if answer == QMessageBox.StandardButton.Save:
            event.accept() if self.save_source() else event.ignore()
        elif answer == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()


def build_application(theme: Theme = DEFAULT) -> "QApplication":
    """The QApplication, in `theme`."""
    app = cast(QApplication, QApplication.instance()) or QApplication([])

    app.setStyle(QStyleFactory.create("Fusion"))
    app.setPalette(qt_palette(theme))

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
