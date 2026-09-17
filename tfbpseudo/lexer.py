"""Tokenizer for TfbPseudo source text."""

import re
from dataclasses import dataclass


@dataclass
class Token:
    kind: str  # STRING, NUMBER, IDENT, NAME, OP, EOF
    value: str
    line: int
    col: int
    pos: int = -1  # absolute offset of the token in the source
    end: int = -1


def synth_token(kind: str, value: str) -> Token:
    """A token that came from an opcode rather than from source text."""
    return Token(kind, value, 0, 0)


TOKEN_SPEC = [
    ("COMMENT", r"//[^\n]*|/\*.*?\*/"),  # // my comment
    ("STRING", r'"(?:[^"\\\n]|\\.)*"'),  # "my string"
    ("NUMBER", r"0x[0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"),  # 123, 1.5, 1e-7
    ("BUILTIN", r"@[A-Za-z_][A-Za-z0-9_]*"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"==|!=|<=|>=|&&|\|\||[{}()\[\];=,.:#+\-*/<>!]"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t\r]+"),
    ("MISMATCH", r"."),
]
MASTER = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC), re.DOTALL)


def tokenize(src: str):
    tokens: list[Token] = []
    line, line_start = 1, 0
    for m in MASTER.finditer(src):
        kind, text = m.lastgroup, m.group()
        col = m.start() - line_start + 1

        if kind == "NEWLINE":
            line += 1
            line_start = m.end()
        elif kind == "SKIP":
            pass
        elif kind == "COMMENT":
            content = text.removeprefix("//")
            tokens.append(Token(kind, content, line, col, m.start(), m.end()))
        elif kind == "MISMATCH":
            raise SyntaxError(f"unexpected character {text!r}, L{line} C{col}")
        elif kind == "STRING":
            value = re.sub(r"\\(.)", r"\1", text[1:-1])
            tokens.append(Token(kind, value, line, col, m.start(), m.end()))
        elif kind == None:
            raise SyntaxError(f"token kind was none, L{line} C{col}")
        else:
            tokens.append(Token(kind, text, line, col, m.start(), m.end()))

    tokens.append(Token("EOF", "", line, len(src) - line_start + 1, len(src), len(src)))
    return tokens
