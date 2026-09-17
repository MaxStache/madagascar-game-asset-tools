"""Colours for the editor: the window chrome and the syntax, in one place.

A theme carries both halves because they have to agree -- syntax colours picked
for a light background are unreadable on a dark one -- so switching swaps them
together.
"""

# pyright: basic

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette


@dataclass(frozen=True)
class Theme:
    name: str

    # ----- chrome -----
    window: str  # menus, status bar
    base: str  # the text area
    text: str
    gutter: str
    gutter_text: str
    gutter_current: str  # the line number the cursor is on
    current_line: str  # the line the cursor is on
    error_line: str  # the line a failed compile points at
    selection: str
    selected_text: str
    disabled: str

    # ----- syntax -----
    comment: str
    string: str
    number: str
    section: str  # globals, locals, prescript, startup, ...
    behavior: str
    flow: str  # flow, end, continue, break, else
    method: str  # a registered opcode method
    unknown_method: str  # anything else called like one, i.e. a typo
    builtin: str  # @myself, @each, @global
    null: str  # @null
    member: str  # the field after a "." or a ":"
    choice: str  # an enum member, and what "#" picks
    call: str  # random(), color(), field[]
    punctuation: str


DARK = Theme(
    name="Dark",
    window="#21252B",
    base="#1E2127",
    text="#ABB2BF",
    gutter="#21252B",
    gutter_text="#5C6370",
    gutter_current="#ABB2BF",
    current_line="#2C313A",
    error_line="#4A2B2F",
    selection="#3E4451",
    selected_text="#FFFFFF",
    disabled="#5C6370",
    comment="#7F848E",
    string="#98C379",
    number="#D19A66",
    section="#C678DD",
    behavior="#C678DD",
    flow="#C678DD",
    method="#61AFEF",
    unknown_method="#FF5370",
    builtin="#E5C07B",
    null="#D19A66",
    member="#E06C75",
    choice="#56B6C2",
    call="#56B6C2",
    punctuation="#8A919E",
)

LIGHT = Theme(
    name="Light",
    window="#DCDCDC",
    base="#DCDCDC",
    text="#101010",
    gutter="#D0D0D0",
    gutter_text="#606060",
    gutter_current="#101010",
    current_line="#E8E8E8",
    error_line="#F3BFBF",
    selection="#2A82DA",
    selected_text="#FFFFFF",
    disabled="#707070",
    comment="#4F7A4F",
    string="#A31515",
    number="#0A7C55",
    section="#00008B",
    behavior="#7A3E9D",
    flow="#AF00DB",
    method="#0451A5",
    unknown_method="#B00020",
    builtin="#8A6D00",
    null="#8A3324",
    member="#0F5C8C",
    choice="#267F99",
    call="#795E26",
    punctuation="#606060",
)

THEMES = {theme.name: theme for theme in (DARK, LIGHT)}
DEFAULT = DARK


def qt_palette(theme: Theme) -> QPalette:
    """The window palette for `theme`, for the Fusion style."""
    window = QColor(theme.window)
    base = QColor(theme.base)
    text = QColor(theme.text)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, window)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, base.lighter(110))
    palette.setColor(QPalette.ColorRole.ToolTipBase, window)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, window)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(theme.unknown_method))
    palette.setColor(QPalette.ColorRole.Link, QColor(theme.method))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.selection))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme.selected_text))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme.disabled))

    # Disabled state, so greyed-out menu entries do not vanish.
    disabled = QColor(theme.disabled)
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled)

    return palette
