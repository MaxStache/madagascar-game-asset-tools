"""What the editor is set to, and the dialog that sets it.

Kept apart from `settings` because the two are different sorts of thing: that
one remembers what happened -- the files opened lately, where each source was
compiled to -- while this one holds what was chosen. What was chosen belongs
somewhere a person can open and read, so it is a JSON file in the usual place
for one (`%LOCALAPPDATA%/tfbpseudo/editor/settings.json` on Windows,
`~/.config/tfbpseudo/editor/settings.json` elsewhere) rather than the registry.

Nothing here raises. A settings file that is missing, unreadable or full of
nonsense leaves the defaults standing: not being able to read a preference is
never a reason to refuse to start.
"""

# pyright: basic

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from tfbpseudo.editor.settings import APPLICATION, ORGANISATION
from tfbpseudo.editor.theme import DEFAULT, THEMES

FILE_NAME = "settings.json"
FONT_MIN, FONT_MAX = 6, 32
SYSTEM_SIZE = 0  # an interface size that leaves the system's own standing

KEEP, DROP = "Keep them", "Leave them out"


@dataclass(frozen=True)
class Preferences:
    """Everything the settings dialog sets, with what it is without one."""

    theme: str = DEFAULT.name
    font_size: int = 12
    # The chrome around the text: the panel, the status bar, the find box.
    interface_font_size: int = SYSTEM_SIZE

    drop_filler_tails: bool = True


def directory() -> Path:
    """Where the settings file goes: this machine's config directory, under
    our own name.
    """
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.GenericConfigLocation,
    )

    return Path(base or Path.home() / ".config") / ORGANISATION / APPLICATION


def path() -> Path:
    return directory() / FILE_NAME


def load() -> Preferences:
    """What the settings file says, as far as it can be read.

    Each preference is taken on its own and only when it is the right sort of
    value, so a file written by a later version -- or hand-edited into
    something odd -- costs the settings it got wrong and no others.
    """
    try:
        stored = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Preferences()

    if not isinstance(stored, dict):
        return Preferences()

    preferences = Preferences()

    theme = stored.get("theme")
    if isinstance(theme, str) and theme in THEMES:
        preferences = replace(preferences, theme=theme)

    size = stored.get("font_size")
    if isinstance(size, int) and not isinstance(size, bool):
        preferences = replace(preferences, font_size=min(max(size, FONT_MIN), FONT_MAX))

    size = stored.get("interface_font_size")
    if isinstance(size, int) and not isinstance(size, bool):
        preferences = replace(
            preferences,
            interface_font_size=(
                SYSTEM_SIZE
                if size == SYSTEM_SIZE
                else min(max(size, FONT_MIN), FONT_MAX)
            ),
        )

    drop = stored.get("drop_filler_tails")
    if isinstance(drop, bool):
        preferences = replace(preferences, drop_filler_tails=drop)

    return preferences


def save(preferences: Preferences) -> bool:
    """Write the settings file, saying whether it went.

    The editor carries on either way: a preference that could not be stored is
    worth a line in the status bar, not a dialog in the way.
    """
    try:
        directory().mkdir(parents=True, exist_ok=True)
        path().write_text(
            json.dumps(asdict(preferences), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return False

    return True


def theme_named(name: str):
    """The theme `name` stands for, or the default when it names none."""
    return THEMES.get(name, DEFAULT)


class SettingsDialog(QDialog):
    """The settings, as a modal dialog.

    It answers with what was chosen and changes nothing itself -- what to do
    about an answer is the window's business, not this one's.
    """

    def __init__(self, preferences: Preferences, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)

        self.theme = QComboBox(self)
        self.theme.addItems(list(THEMES))
        self.theme.setCurrentText(theme_named(preferences.theme).name)

        self.font_size = QSpinBox(self)
        self.font_size.setRange(FONT_MIN, FONT_MAX)
        self.font_size.setValue(preferences.font_size)
        self.font_size.setSuffix(" pt")

        # One step below the smallest size stands for the system's own, so
        # going back to it is just scrolling down.
        self.interface_font_size = QSpinBox(self)
        self.interface_font_size.setRange(FONT_MIN - 1, FONT_MAX)
        self.interface_font_size.setSpecialValueText("System default")
        self.interface_font_size.setValue(
            preferences.interface_font_size or FONT_MIN - 1,
        )
        self.interface_font_size.setSuffix(" pt")

        self.filler = QComboBox(self)
        self.filler.addItems([KEEP, DROP])
        self.filler.setCurrentText(DROP if preferences.drop_filler_tails else KEEP)

        note = QLabel(
            "A reference used as a value carries a `+ 0` that the engine reads "
            "whether or not it says anything. Leaving them out changes the "
            "text and not the script: the compiler writes them back where they "
            "belong.",
            self,
        )
        note.setTextFormat(Qt.TextFormat.PlainText)
        note.setWordWrap(True)
        note.setMinimumWidth(320)
        note.setEnabled(False)  # said quietly: it explains, it does not ask

        form = QFormLayout()
        form.addRow("Theme", self.theme)
        form.addRow("Editor text size", self.font_size)
        form.addRow("Interface text size", self.interface_font_size)
        form.addRow("`+ 0` when decompiling", self.filler)
        form.addRow("", note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def chosen(self) -> Preferences:
        """What the dialog was left saying."""
        interface = self.interface_font_size.value()

        return Preferences(
            theme=self.theme.currentText(),
            font_size=self.font_size.value(),
            interface_font_size=SYSTEM_SIZE if interface < FONT_MIN else interface,
            drop_filler_tails=self.filler.currentText() == DROP,
        )
