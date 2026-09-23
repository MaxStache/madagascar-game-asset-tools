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
    warning: str  # a problem worth saying, that still compiles
    selection: str
    selected_text: str
    disabled: str
    overlay: str  # a panel floating over the text, i.e. the find box
    border: str
    indent_guide: str  # the vertical rule down each level of indentation
    brace: str  # the pair of braces the cursor is sitting on
    scroll_track: str  # the channel a scrollbar runs in
    scroll_handle: str  # the bar itself, which has to read against the text
    scroll_handle_hover: str

    # ----- find -----
    match: str  # every hit for the current query
    current_match: str  # the one the find box is sitting on

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
    warning="#D19A66",
    selection="#3E4451",
    selected_text="#FFFFFF",
    disabled="#5C6370",
    overlay="#2C313A",
    border="#4B5263",
    indent_guide="#3B4048",
    brace="#455063",
    scroll_track="#21252B",
    scroll_handle="#7C8494",
    scroll_handle_hover="#99A1B1",
    match="#4A3A22",
    current_match="#9E6A2E",
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
    window="#EAEAEB",
    base="#FAFAFA",
    text="#383A42",
    gutter="#EAEAEB",
    gutter_text="#9D9D9F",
    gutter_current="#383A42",
    current_line="#F0F0F1",
    error_line="#F9DADC",
    warning="#986801",
    selection="#D5D9E2",
    selected_text="#232324",
    disabled="#A0A1A7",
    overlay="#F0F0F1",
    border="#C8C9CD",
    indent_guide="#E0E0E2",
    brace="#D3D8E3",
    scroll_track="#EAEAEB",
    scroll_handle="#B4B6BC",
    scroll_handle_hover="#9A9CA3",
    match="#F5E4C3",
    current_match="#E8B96A",
    comment="#A0A1A7",
    string="#50A14F",
    number="#986801",
    section="#A626A4",
    behavior="#A626A4",
    flow="#A626A4",
    method="#4078F2",
    unknown_method="#CA1243",
    builtin="#C18401",
    null="#986801",
    member="#E45649",
    choice="#0184BC",
    call="#0184BC",
    punctuation="#696C77",
)

NORD = Theme(
    name="Nord",
    window="#272C36",
    base="#2E3440",
    text="#D8DEE9",
    gutter="#272C36",
    gutter_text="#4C566A",
    gutter_current="#D8DEE9",
    current_line="#3B4252",
    error_line="#4B3339",
    warning="#D08770",
    selection="#434C5E",
    selected_text="#ECEFF4",
    disabled="#616E88",
    overlay="#3B4252",
    border="#4C566A",
    indent_guide="#3B4252",
    brace="#4C566A",
    scroll_track="#272C36",
    scroll_handle="#616E88",
    scroll_handle_hover="#7B88A1",
    match="#4A4538",
    current_match="#8A7442",
    comment="#6D7A91",
    string="#A3BE8C",
    number="#B48EAD",
    section="#81A1C1",
    behavior="#81A1C1",
    flow="#81A1C1",
    method="#88C0D0",
    unknown_method="#BF616A",
    builtin="#EBCB8B",
    null="#B48EAD",
    member="#D08770",
    choice="#8FBCBB",
    call="#8FBCBB",
    punctuation="#7B88A1",
)

CATPPUCCIN_MOCHA = Theme(
    name="Catppuccin Mocha",
    window="#181825",
    base="#1E1E2E",
    text="#CDD6F4",
    gutter="#181825",
    gutter_text="#6C7086",
    gutter_current="#B4BEFE",
    current_line="#2A2B3C",
    error_line="#3D2A36",
    warning="#FAB387",
    selection="#45475A",
    selected_text="#CDD6F4",
    disabled="#6C7086",
    overlay="#313244",
    border="#45475A",
    indent_guide="#313244",
    brace="#585B70",
    scroll_track="#181825",
    scroll_handle="#6C7086",
    scroll_handle_hover="#7F849C",
    match="#4A4234",
    current_match="#8C6E4A",
    comment="#7F849C",
    string="#A6E3A1",
    number="#FAB387",
    section="#CBA6F7",
    behavior="#CBA6F7",
    flow="#CBA6F7",
    method="#89B4FA",
    unknown_method="#F38BA8",
    builtin="#F9E2AF",
    null="#FAB387",
    member="#B4BEFE",
    choice="#94E2D5",
    call="#89DCEB",
    punctuation="#9399B2",
)

THEMES = {theme.name: theme for theme in (DARK, LIGHT, NORD, CATPPUCCIN_MOCHA)}
DEFAULT = DARK


def scrollbar_style(theme: Theme) -> str:
    return f"""
    QScrollBar:vertical {{
        background: {theme.scroll_track};
        width: 13px;
        margin: 0;
        border: none;
    }}
    QScrollBar:horizontal {{
        background: {theme.scroll_track};
        height: 13px;
        margin: 0;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {theme.scroll_handle};
        min-height: 28px;
        border-radius: 4px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {theme.scroll_handle};
        min-width: 28px;
        border-radius: 4px;
        margin: 2px;
    }}
    QScrollBar::handle:hover {{ background: {theme.scroll_handle_hover}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0;
        height: 0;
        border: none;
        background: none;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
    QAbstractScrollArea::corner {{ background: {theme.scroll_track}; }}
    """


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
