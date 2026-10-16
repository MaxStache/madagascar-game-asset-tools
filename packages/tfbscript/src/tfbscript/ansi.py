"""Centralized ANSI syntax highlighting for TFBScript pretty-printing.

Usage:
    from tfbscript.ansi import keyword

    print(keyword("var"))

Coloring is on by default when stdout is a real terminal, and off when
piped/redirected or when the NO_COLOR env var is set (https://no-color.org).
Override explicitly with enable_colors() / disable_colors() / set_colors_enabled(),
e.g. to add a --no-color CLI flag to a script.
"""

import os
import sys
from enum import Enum

_RESET = "\033[0m"


if sys.platform == "win32":

    def _enable_windows_vt100() -> bool:
        """Turn on ANSI (virtual terminal) processing for the Windows console."""
        try:
            import ctypes

            STD_OUTPUT_HANDLE = -11
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

            mode = ctypes.c_uint32()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                return False

            return bool(
                kernel32.SetConsoleMode(
                    handle,
                    mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING,
                )
            )
        except Exception:  # noqa: BLE001
            return False

else:

    def _enable_windows_vt100() -> bool:
        """No-op on non-Windows platforms."""
        return True


def _detect_default() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") is not None:
        return True
    if not getattr(sys.stdout, "isatty", lambda: False)():
        return False
    if sys.platform == "win32":
        return _enable_windows_vt100()
    return True


_enabled = _detect_default()


def colors_enabled() -> bool:
    return _enabled


def set_colors_enabled(value: bool) -> None:
    global _enabled
    _enabled = value


def enable_colors() -> None:
    set_colors_enabled(True)


def disable_colors() -> None:
    set_colors_enabled(False)


def _fg_rgb(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _fg(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return _fg_rgb(r, g, b)


class Color(Enum):
    """Syntax categories, colored after the One Dark Pro theme."""

    # Punctuation
    PARENTHESES = "#5C6370"  # muted gray

    # Operators
    OPERATOR = "#56B6C2"  # cyan
    COMPARISON = "#56B6C2"  # cyan

    # Language keywords
    KEYWORD = "#C678DD"  # purple
    FLOW_CONTROL = "#E06C75"  # red

    # Literals
    STRING = "#98C379"  # green
    NUMBER = "#D19A66"  # orange
    TYPE = "#E5C07B"  # yellow
    BUILTIN = "#E5C07B"  # yellow

    # Identifiers
    VARIABLE = "#E06C75"  # red
    VARIABLE_GLOBAL = "#61AFEF"  # blue
    METHOD = "#61AFEF"  # blue

    # Comments
    COMMENT = "#5C6370"  # muted gray

    INLINE_FUNC_OP = "#6458EC"


def color_text(text: object, color: Color) -> str:
    """Wrap text in `color`'s ANSI code; passes it through unchanged if coloring is off."""
    if not _enabled:
        return str(text)
    return f"{_fg(color.value)}{text}{_RESET}"


# Shorthand for each syntax category, e.g. keyword("if") instead of
# color_text("if", Color.KEYWORD) -- use these when building source_line()
# output for opcodes so call sites read like the syntax they represent.
def parentheses(text: object) -> str:
    return color_text(text, Color.PARENTHESES)


def operator(text: object) -> str:
    return color_text(text, Color.OPERATOR)


def comparison(text: object) -> str:
    return color_text(text, Color.COMPARISON)


def keyword(text: object) -> str:
    return color_text(text, Color.KEYWORD)


def flow_control(text: object) -> str:
    return color_text(text, Color.FLOW_CONTROL)


def string(text: object) -> str:
    return color_text(text, Color.STRING)


def number(text: object) -> str:
    return color_text(text, Color.NUMBER)


def type_(text: object) -> str:
    return color_text(text, Color.TYPE)


def builtin(text: object) -> str:
    return color_text(text, Color.BUILTIN)


def variable(text: object) -> str:
    return color_text(text, Color.VARIABLE)


def variable_global(text: object) -> str:
    return color_text(text, Color.VARIABLE_GLOBAL)


def method(text: object) -> str:
    return color_text(text, Color.METHOD)


def comment(text: object) -> str:
    return color_text(text, Color.COMMENT)


def rgb_square(r: int, g: int, b: int) -> str:
    """A small ■ swatch rendered in the given RGB, e.g. to preview a Color32 value."""
    if not _enabled:
        return ""
    return f"{_fg_rgb(r, g, b)}■ {_RESET}"


def quoted_string(text: str) -> str:
    return string(f'"{text}"')


def func_call(func_name: str, *args: str, add_semicolon=True) -> str:
    """Format a function call with syntax highlighting."""
    args_str = ", ".join(args)
    return f"{method(func_name)}{parentheses('(')}{args_str}{parentheses(')')}{';' if add_semicolon else ''}"
