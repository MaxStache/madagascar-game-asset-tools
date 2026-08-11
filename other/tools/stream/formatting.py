"""Hex dumping and pretty-printing of parsed section objects."""

import re

# Characters that drive the format_repr state machine; everything between two
# matches is plain text that can be copied in bulk.
_SPECIAL = re.compile(r"""[()\[\],'"]""")


def _find_closing_quote(text: str, quote: str, start: int) -> int:
    """Index of the closing quote at/after `start`, or len(text) if none.

    Matches the original scanner's escape rule: a quote is skipped only when
    the single preceding character is a backslash.
    """
    j = start
    while True:
        j = text.find(quote, j)
        if j == -1:
            return len(text)
        if text[j - 1] != "\\":
            return j
        j += 1

def truncate_repr_strings(
    text: str, max_str_len: int = 150, max_total_len: int | None = None
) -> str:
    """Replace over-long quoted strings with a placeholder.

    If `max_total_len` is given, processing stops once the output exceeds it —
    callers that only display a prefix (see pretty_object) then don't pay for
    scanning the full input. The returned prefix up to `max_total_len` is
    identical to the untruncated result.
    """
    result = []
    total = 0
    i = 0
    n = len(text)

    while i < n:
        if max_total_len is not None and total > max_total_len:
            break

        # Jump straight to the next quote; everything before it passes through.
        dq = text.find('"', i)
        sq = text.find("'", i)

        if dq == -1 and sq == -1:
            result.append(text[i:])
            break

        if dq == -1:
            q = sq
        elif sq == -1:
            q = dq
        else:
            q = min(dq, sq)

        if q > i:
            result.append(text[i:q])
            total += q - i

        quote = text[q]
        j = _find_closing_quote(text, quote, q + 1)

        if j - q - 1 > max_str_len:
            result.append(quote + "TOO LONG TO DISPLAY" + quote)
            total += 21
        else:
            result.append(text[q : j + 1])
            total += j + 1 - q

        i = j + 1

    return "".join(result)


def format_repr(
    text: str,
    indent_size: int = 4,
    max_str_len: int = 150,
    max_list_items: int = 10,
) -> str:
    lines = []

    indent = 0
    current = ""

    # Stack of open brackets: "(" or "["
    stack = []

    # State for open lists
    list_stack = []

    i = 0
    n = len(text)

    while i < n:
        # ------------------------------------------------------------
        # Skip the remainder of a truncated list
        # ------------------------------------------------------------
        if list_stack and list_stack[-1]["skipping"]:
            state = list_stack[-1]

            # Plain characters are discarded here, so jump between the
            # structural characters directly.
            m = _SPECIAL.search(text, i)
            if m is None:
                break
            i = m.start()
            char = text[i]

            if char in "\"'":
                i = _find_closing_quote(text, char, i + 1)

            elif char in "([":
                stack.append(char)

            elif char == ")":
                if stack:
                    stack.pop()

            elif char == ",":
                # Count remaining top-level list elements
                if len(stack) == state["depth"]:
                    state["skipped"] += 1

            elif char == "]":
                if len(stack) == state["depth"]:
                    indent -= 1

                    skipped = state["skipped"]
                    if skipped > 0:
                        skipped += 1  # final item

                    lines.append(
                        " " * (indent * indent_size)
                        + f"# ... Truncated, {skipped} more object{'s' if skipped != 1 else ''})"
                    )
                    stack.pop()
                    list_stack.pop()
                    current = "]"
                else:
                    if stack:
                        stack.pop()

            i += 1
            continue

        # ------------------------------------------------------------
        # Normal parsing
        # ------------------------------------------------------------
        m = _SPECIAL.search(text, i)
        if m is None:
            current += text[i:]
            break

        if m.start() > i:
            current += text[i : m.start()]
            i = m.start()

        char = text[i]

        if char in "([":
            stack.append(char)

            if char == "[":
                list_stack.append(
                    {
                        "depth": len(stack),
                        "items": 0,
                        "skipping": False,
                        "skipped": 0,
                    }
                )

            # Empty brackets stay inline
            if i + 1 < n and text[i + 1] in ")]":
                current += char + text[i + 1]

                stack.pop()
                if char == "[":
                    list_stack.pop()

                i += 1

            else:
                current += char
                lines.append(" " * (indent * indent_size) + current.strip())
                current = ""
                indent += 1

        elif char in ")]":
            if current.strip():
                lines.append(" " * (indent * indent_size) + current.strip())

            indent -= 1
            current = char

            if stack:
                opening = stack.pop()

                if opening == "[" and list_stack:
                    list_stack.pop()

        elif char == ",":
            current += ","

            # Only count commas separating top-level list items
            if (
                list_stack
                and stack
                and stack[-1] == "["
                and len(stack) == list_stack[-1]["depth"]
            ):
                list_stack[-1]["items"] += 1

                if list_stack[-1]["items"] >= max_list_items:
                    lines.append(" " * (indent * indent_size) + current.strip())
                    current = ""
                    list_stack[-1]["skipping"] = True
                    i += 1
                    continue

            lines.append(" " * (indent * indent_size) + current.strip())
            current = ""

        else:  # quote
            quote = char
            j = _find_closing_quote(text, quote, i + 1)

            inner = text[i + 1 : j]

            if len(inner) > max_str_len:
                current += quote + "TOO LONG TO DISPLAY" + quote
            else:
                current += quote + inner + quote

            i = j

        i += 1

    if current.strip():
        lines.append(" " * (indent * indent_size) + current.strip())

    return "\n".join(lines)


def pretty_object(obj):
    # Only the first 200k chars are ever displayed, so stop scanning there.
    representation = truncate_repr_strings(repr(obj), max_total_len=200_000)

    if len(representation) > 200_000:
        return (
            "# CUTOFF AFTER 200.000 CHARACTERS!\n\n"
            + format_repr(representation[:200_000], indent_size=4)
            + "\n#                 ... (truncated) ...\n\n\n"
        )
    return format_repr(representation, indent_size=4)
