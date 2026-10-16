# pyright: basic

import io
from pathlib import Path

from fontTools.ttLib import TTFont

from PySide6.QtGui import QFont, QFontDatabase


def load_font(
    path: str | Path,
    size: int = 11,
    weight: QFont.Weight = QFont.Weight.Normal,
    italic: bool = False,
    aliased: bool = True,
) -> QFont:
    """
    Load a custom font from file, rendered GDI-style (grid-fitted, no AA).

    Args:
        path: Path to the font file (.ttf, .otf, etc.), or a Qt resource path
        size: Size in PIXELS (not points) — 11px == XP's default 8pt Tahoma
        weight: Font weight (e.g. QFont.Weight.Normal, QFont.Weight.Bold)
        italic: Whether the font should be italic
        aliased: True for crisp XP "standard" text, False for soft ClearType-ish text

    Returns:
        The QFont instance.

    Raises:
        ValueError: if the font file could not be loaded.
    """
    font_id = QFontDatabase.addApplicationFont(str(path))

    if font_id == -1:
        raise ValueError(f"Failed to load font from: {path}")

    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        raise ValueError(f"No font families found in: {path}")

    font = QFont(families[0])
    font.setPixelSize(size)  # pixel size, so DPI can't rescale us into mush
    font.setWeight(weight)
    font.setItalic(italic)

    if aliased:
        # Hard pixel edges + snap stems to the pixel grid == comctl32 look
        font.setStyleStrategy(
            QFont.StyleStrategy(
                QFont.StyleStrategy.NoAntialias | QFont.StyleStrategy.PreferMatch
            )
        )
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    else:
        # Soft, slightly smeared — closer to ClearType on a non-LCD display
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

    return font


def register_bold_variant(regular_family: str, bold_path: str | Path) -> None:
    """
    Load `bold_path` as the Bold weight of `regular_family`.

    The bold TTF's own name/OS2 tables declare it as an unrelated Regular-weight
    family (e.g. "MS Sans Serif Bold" @ weight 400), so Qt registers it as a
    separate font family and `font-weight: bold` on the regular family just
    synthesizes a fake bold instead of using the real hinted glyphs. Patch the
    tables in memory so Qt sees it as `regular_family`'s Bold style.
    """
    font = TTFont(str(bold_path))

    name = font["name"]
    for name_id, value in (
        (1, regular_family),
        (2, "Bold"),
        (4, f"{regular_family} Bold"),
        (16, regular_family),
        (17, "Bold"),
    ):
        name.setName(value, name_id, 3, 1, 0x409)
        name.setName(value, name_id, 1, 0, 0)

    os2 = font["OS/2"]
    os2.usWeightClass = 700  # pyright: ignore[reportAttributeAccessIssue]
    os2.fsSelection = (  # pyright: ignore[reportAttributeAccessIssue]
        os2.fsSelection & ~0x40  # pyright: ignore[reportAttributeAccessIssue]
    ) | 0x20  # clear REGULAR, set BOLD
    font["head"].macStyle |= 0x1  # pyright: ignore[reportAttributeAccessIssue]

    buf = io.BytesIO()
    font.save(buf)

    if QFontDatabase.addApplicationFontFromData(buf.getvalue()) == -1:
        raise ValueError(f"Failed to register bold variant from: {bold_path}")
