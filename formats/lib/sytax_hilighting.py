from enum import Enum


def text_rgb_square(r, g, b):
    return f"\033[38;2;{r};{g};{b}m■ \033[0m"


def ANSI_COLOR(color):
    if isinstance(color, str):
        color = color.lstrip("#")
        if len(color) != 6:
            raise ValueError("Hex color must be 6 characters (e.g. #ff0000)")
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    else:
        r, g, b = color

    return f"\033[38;2;{r};{g};{b}m"


class Color(Enum):
    REFERENCE = ANSI_COLOR("#e06c75")
    NUMBER = ANSI_COLOR("#d19a66")
    OPERATOR = ANSI_COLOR("#56b6c2")
    METHOD = ANSI_COLOR("#61afef")
    RGBACOLOR = ANSI_COLOR("#98c379")
    STRING = ANSI_COLOR("#98c379")
    COMMENT = ANSI_COLOR("#5c6370")
    ENUM_VALUE = ANSI_COLOR("#c678dd")
    RESET = "\033[0m"


def color_text(text: str, color: Color) -> str:
    return f"{color.value}{text}{Color.RESET.value}"