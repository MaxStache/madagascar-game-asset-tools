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
    window="#DCDCDC",
    base="#DCDCDC",
    text="#101010",
    gutter="#D0D0D0",
    gutter_text="#606060",
    gutter_current="#101010",
    current_line="#E8E8E8",
    error_line="#F3BFBF",
    warning="#8A6D00",
    selection="#2A82DA",
    selected_text="#FFFFFF",
    disabled="#707070",
    overlay="#E8E8E8",
    border="#A8A8A8",
    indent_guide="#BFBFBF",
    brace="#C3CBD6",
    scroll_track="#D0D0D0",
    scroll_handle="#9B9B9B",
    scroll_handle_hover="#7E7E7E",
    match="#FFF2A8",
    current_match="#FFC63F",
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


def scrollbar_style(theme: Theme) -> str:
    """The scrollbars, for the whole application.

    Fusion draws them out of the palette, which on a dark theme puts a bar
    nearly the colour of the text area next to it -- so they are styled by
    hand instead. A stylesheet has to say everything: the arrow buttons and
    the pages either side of the handle are turned off here rather than left
    for the default style to draw around what is styled.
    """
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
