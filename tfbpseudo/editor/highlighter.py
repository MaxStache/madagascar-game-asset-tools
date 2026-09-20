"""Syntax highlighting for TfbPseudo source.

The word lists are taken from the registries themselves -- the methods from
METHOD_OPCODE_TABLE, the enum members from tfbscript's own enums, the builtins
and scope names from `references` -- so adding an opcode lights it up without
anyone having to remember this file. The words that are TfbPseudo's own, and
the shape of a name, are shared with `completions`: what is highlighted as a
section or a flow word is what is completed as one.
"""

# pyright: basic

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from tfbpseudo.compiler import METHOD_OPCODE_TABLE
from tfbpseudo.editor.completions import (
    FLOW_WORDS,
    NAME,
    SECTIONS,
    enum_members,
)
from tfbpseudo.editor.theme import DEFAULT, Theme
from tfbpseudo.references import (
    BUILTIN_TOKENS,
    MEMBER_INDEX_WORD,
    NULL_BUILTIN_TOKEN,
    SCOPE_BY_NAME,
    SCOPE_INDEX_WORD,
    SUB_INDEX_WORD,
    TABLE_TOKENS,
)
from tfbpseudo.rhs import CALLS

INDEX_WORDS = (MEMBER_INDEX_WORD, SUB_INDEX_WORD, SCOPE_INDEX_WORD)


def word_pattern(words) -> str:
    return r"\b(?:" + "|".join(QRegularExpression.escape(w) for w in words) + r")\b"


def char_format(color: str | QColor, bold: bool = False, italic: bool = False):
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


class TfbPseudoHighlighter(QSyntaxHighlighter):
    """Highlights one TfbPseudo document.

    Rules are applied in order and later ones win, so strings and comments come
    last: whatever they contain is not code.
    """

    BLOCK_COMMENT = 1  # carried between lines for /* ... */

    def __init__(self, document, theme: Theme = DEFAULT):
        super().__init__(document)
        self.theme = theme
        self.build_rules()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.build_rules()
        self.rehighlight()

    def build_rules(self) -> None:
        theme = self.theme

        methods = sorted(METHOD_OPCODE_TABLE, key=len, reverse=True)
        builtins = sorted(
            list(BUILTIN_TOKENS) + list(TABLE_TOKENS), key=len, reverse=True
        )

        # (pattern, format, which capture group to paint -- 0 is the whole match)
        self.rules: list[tuple[QRegularExpression, QTextCharFormat, int]] = []

        def rule(pattern: str, fmt: QTextCharFormat, group: int = 0) -> None:
            self.rules.append((QRegularExpression(pattern), fmt, group))

        # Anything called like a method, so an unknown one stands out as a typo
        # before the compiler is ever run.
        rule(rf"\b({NAME})\s*\(", char_format(theme.unknown_method), 1)
        rule(
            word_pattern(methods) + r"(?=\s*\()",
            char_format(theme.method, bold=True),
        )
        rule(word_pattern(CALLS) + r"(?=\s*\()", char_format(theme.call))
        rule(word_pattern(INDEX_WORDS) + r"(?=\s*\[)", char_format(theme.call))

        rule(word_pattern(SECTIONS), char_format(theme.section, bold=True))
        rule(r"\bbehavior\b", char_format(theme.behavior, bold=True))
        rule(word_pattern(FLOW_WORDS), char_format(theme.flow, bold=True))

        # A member or a sub: the field named after a "." or a ":".
        rule(rf"[.:]\s*({NAME})", char_format(theme.member), 1)
        # The element a "#" picks out of a set.
        rule(
            r"#\s*(" + "|".join(SCOPE_BY_NAME) + r")\b",
            char_format(theme.choice, bold=True),
            1,
        )

        # An enum member, but only where an argument can be -- these are
        # ordinary words like `add` and `local` and would light up everywhere.
        rule(
            r"[(,]\s*(" + "|".join(enum_members()) + r")\s*(?=[,)])",
            char_format(theme.choice),
            1,
        )

        rule(QRegularExpression.escape(NULL_BUILTIN_TOKEN), char_format(theme.null))
        rule("|".join(QRegularExpression.escape(b) for b in builtins),
             char_format(theme.builtin, bold=True))

        rule(r"\b0[xX][0-9A-Fa-f]+\b|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b",
             char_format(theme.number))
        rule(r"[{}()\[\];,.:#=+\-*/<>!]|==|!=|<=|>=",
             char_format(theme.punctuation))

        # Last, so nothing inside them is painted as code.
        rule(r'"(?:[^"\\\n]|\\.)*"', char_format(theme.string))
        rule(r"//[^\n]*", char_format(theme.comment, italic=True))

        self.comment_format = char_format(theme.comment, italic=True)
        self.comment_start = QRegularExpression(r"/\*")
        self.comment_end = QRegularExpression(r"\*/")

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt, group in self.rules:
            matches = pattern.globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                start = match.capturedStart(group)
                if start >= 0:
                    self.setFormat(start, match.capturedLength(group), fmt)

        self.highlight_block_comment(text)

    def highlight_block_comment(self, text: str) -> None:
        """`/* ... */`, which can run across lines -- the state says whether
        this line started inside one."""
        self.setCurrentBlockState(0)

        start = 0
        if self.previousBlockState() != self.BLOCK_COMMENT:
            start = text.find("/*")

        while start >= 0:
            end = self.comment_end.match(text, start)

            if end.hasMatch():
                length = end.capturedEnd() - start
                self.setCurrentBlockState(0)
            else:
                length = len(text) - start
                self.setCurrentBlockState(self.BLOCK_COMMENT)

            self.setFormat(start, length, self.comment_format)
            start = text.find("/*", start + length)
