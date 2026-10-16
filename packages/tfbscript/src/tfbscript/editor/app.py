# pyright: basic

import os
import signal
from pathlib import Path
from typing import cast

from tfbscript.ansi import set_colors_enabled
from tfbscript.script import ScriptFile

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QAction, QFont, QFontDatabase, QKeySequence
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QStyleFactory,
        QTreeWidget,
        QVBoxLayout,
        QWidget,
        QMessageBox,
    )
except ModuleNotFoundError:
    print("WARN: PySide6 not installed, editor wont work")

from .fonts import register_bold_variant
from .search import SearchBar, SearchEntry, TreeSearch
from .style import build_palette, Win98TreeStyle
from .widgets import populate_tree

import yaml

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

signal.signal(signal.SIGINT, signal.SIG_DFL)

set_colors_enabled(False)


def editor_from_filepath(filepath: Path | str):
    script = ScriptFile.from_path(filepath)
    open_editor(script)


def open_editor(script: ScriptFile):
    app = cast(QApplication, QApplication.instance()) or QApplication([])

    SCRIPT_DIR = Path(__file__).resolve().parent

    window = QMainWindow()
    window.setWindowTitle("TFBScript Editor")
    window.resize(1200, 720)

    app.setStyle(Win98TreeStyle(QStyleFactory.create("Fusion")))

    QFontDatabase.addApplicationFont(
        str(Path(SCRIPT_DIR, "fonts", "ms-sans-serif", "MS Sans Serif.ttf"))
    )
    register_bold_variant(
        "MS Sans Serif",
        Path(SCRIPT_DIR, "fonts", "ms-sans-serif-bold", "MS Sans Serif Bold.ttf"),
    )

    if not Path("EDITOR.yaml").exists():
        cfg = {"appereance": {"font": "MS Sans Serif"}}
    else:
        with open("EDITOR.yaml", "r") as f:
            cfg = yaml.safe_load(f)

    font_name = cfg.get("appereance", {}).get("font", "MS Sans Serif")

    font = QFont(font_name)
    font.setPixelSize(13)
    font.setBold(True)
    app.setFont(font)

    app.setPalette(build_palette())

    def save() -> None:
        print("SAVE SAVE SAVE")
        if script._file_path is not None:
            with open(
                script._file_path,
                "wb",
            ) as f:
                script.write(f)
        else:
            QMessageBox.critical(None, "Save Failed", "FILE WAS OPENED WITHOUT A _file_path")

    def expand_all() -> None:
        tree.expandAll()

    file_menu = window.menuBar().addMenu("File")
    file_menu.addAction("Save").triggered.connect(save)

    other_menu = window.menuBar().addMenu("Other")

    expand_all_action = QAction("Expand All", other_menu)

    expand_all_action.setShortcut(
        QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_E)
    )
    expand_all_action.triggered.connect(expand_all)

    other_menu.addAction(expand_all_action)

    find_action = QAction("Find", other_menu)
    find_action.setShortcut(QKeySequence.StandardKey.Find)
    other_menu.addAction(find_action)

    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
    tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    tree.setRootIsDecorated(True)
    tree.setItemsExpandable(True)
    tree.setIndentation(40)
    tree.itemClicked.connect(
        lambda item, column: item.setExpanded(not item.isExpanded())
    )

    search_index: list[SearchEntry] = []
    for opcode in script.instructions:
        populate_tree(tree, opcode, search_index)

    search_bar = SearchBar()
    search = TreeSearch(tree, search_bar, search_index)
    find_action.triggered.connect(search.open)

    central = QWidget()
    central_layout = QVBoxLayout(central)
    central_layout.setContentsMargins(0, 0, 0, 0)
    central_layout.setSpacing(0)
    central_layout.addWidget(tree, 1)
    central_layout.addWidget(search_bar)

    window.setCentralWidget(central)
    window.show()

    app.exec()
