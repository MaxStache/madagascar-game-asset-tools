"""Lightweight Python syntax highlighting for a tk.Text widget."""

import io
import keyword
import tkinter as tk
import tokenize

from .theme import COLORS

# Token types that do not count as "meaningful" when looking ahead.
_SKIP = (
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
)

# Tags configured once via `configure_tags`; also the set cleared per render.
_TAGS = (
    "classname",
    "kwarg",
    "number",
    "string",
    "constant",
    "punct",
    "comment",
    "enum_class",
    "enum_value",
)


def _next_meaningful(toks, idx):
    for j in range(idx + 1, len(toks)):
        if toks[j].type not in _SKIP:
            return toks[j].string
    return None


def _next_token(toks, idx):
    if idx + 1 < len(toks):
        return toks[idx + 1].string
    return None


def _get_tokens(code: str):
    toks = []
    readline = io.StringIO(code).readline

    try:
        for tok in tokenize.generate_tokens(readline):
            toks.append(tok)
    except tokenize.TokenError:
        # Keep tokens before the incomplete part
        pass
    except IndentationError:
        pass

    return toks


def configure_tags(widget: tk.Text):
    """Set up highlight colors once, at widget creation time."""
    for name in _TAGS:
        widget.tag_configure(name, foreground=COLORS[name])
    # Comments must win over any overlapping tag.
    widget.tag_raise("comment")


def highlight(widget: tk.Text, code: str):
    widget.delete("1.0", tk.END)
    widget.insert("1.0", code)

    # Drop tags from the previous render (text delete clears ranges, but be
    # explicit in case the widget is reused without a full clear).
    for name in _TAGS:
        widget.tag_remove(name, "1.0", tk.END)

    toks = _get_tokens(code)

    # Accumulate index pairs per tag, then add each tag in a single Tcl call.
    ranges: dict[str, list[str]] = {}

    for idx, tok in enumerate(toks):
        tag = None
        t = tok.type

        if t == tokenize.COMMENT:
            tag = "comment"

        elif t == tokenize.NAME:
            prev = toks[idx - 1].string if idx > 0 else None
            raw_next = _next_token(toks, idx)
            s = tok.string

            if raw_next == ".":
                tag = "enum_class"
            elif prev == ".":
                tag = "enum_value"
            elif s in ("True", "False", "None") or keyword.iskeyword(s):
                tag = "constant"
            else:
                # Only pay for the look-ahead scan when nothing cheaper matched.
                nxt = _next_meaningful(toks, idx)
                if nxt == "(":
                    tag = "classname"
                elif nxt == "=":
                    tag = "kwarg"

        elif t == tokenize.NUMBER:
            tag = "number"

        elif t == tokenize.STRING:
            tag = "string"

        elif t == tokenize.OP:
            tag = "punct"

        if tag:
            r = ranges.setdefault(tag, [])
            r.append(f"{tok.start[0]}.{tok.start[1]}")
            r.append(f"{tok.end[0]}.{tok.end[1]}")

    for tag, idxs in ranges.items():
        widget.tag_add(tag, *idxs)
