"""Hex dumping and pretty-printing of parsed section objects."""

from analyze.theme import COLORS


def hexdump(widget, data, width=8, parse_end=0x0):
    blocks_per_chunk = width // 8
    block_size = 8

    def byte_col(k):
        # 10 = 8-char offset field + two spaces before the hex bytes.
        # Each block is block_size*3-1 chars, blocks separated by two spaces.
        block, pos = divmod(k, block_size)
        return 10 + block * (block_size * 3 + 1) + pos * 3

    for name in (
        "hex_read",
        "hex_not_read",
        "hex_offset",
        "hex_ascii",
    ):
        widget.tag_configure(name, foreground=COLORS[name])

    read_tagging_offset = 0
    prefix = ""

    if len(data) > 15_000:
        # Four header lines; data lines start at line 5, matching the offset.
        prefix = (
            "\n"
            f"Data too long to display ({len(data)} bytes).\n"
            "Showing first 15,000 bytes:\n"
            "\n"
        )
        data = data[:15_000]
        read_tagging_offset = 4

    # Build the whole dump as one string and accumulate tag ranges, then issue
    # a single insert and one tag_add per tag. Inserting line-by-line with a
    # handful of tag_add calls each was thousands of Tcl round-trips per click.
    text_parts = []
    ranges = {"hex_offset": [], "hex_not_read": [], "hex_read": [], "hex_ascii": []}

    for off in range(0, len(data), width):
        line = off // width + 1 + read_tagging_offset

        chunk = data[off : off + width]

        chunk_blocks = [
            " ".join(f"{b:02X}" for b in chunk[i * 8 : (i + 1) * 8])
            for i in range(blocks_per_chunk)
        ]

        hex_part = "  ".join(chunk_blocks)
        hex_part = hex_part.ljust(width * 3 - 1)

        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)

        line_text = f"{off:08X}  {hex_part}  {ascii_part}\n"
        text_parts.append(line_text)

        ranges["hex_offset"] += [f"{line}.0", f"{line}.8"]

        end_written = len(line_text) - len(ascii_part)
        ranges["hex_not_read"] += [f"{line}.10", f"{line}.{end_written + 10}"]

        read_in_line = max(0, min(parse_end - off, len(chunk)))
        if read_in_line > 0:
            read_end_col = byte_col(read_in_line - 1) + 2
            ranges["hex_read"] += [f"{line}.10", f"{line}.{read_end_col}"]

        ascii_part_start = 8 + len("  ") + len(hex_part) + len("  ")
        ranges["hex_ascii"] += [
            f"{line}.{ascii_part_start}",
            f"{line}.{ascii_part_start + width}",
        ]

    widget.insert("1.0", prefix + "".join(text_parts))

    for tag, idxs in ranges.items():
        if idxs:
            widget.tag_add(tag, *idxs)

    widget.tag_raise("hex_read")

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

    while i < len(text):
        char = text[i]

        # ------------------------------------------------------------
        # Skip the remainder of a truncated list
        # ------------------------------------------------------------
        if list_stack and list_stack[-1]["skipping"]:
            state = list_stack[-1]

            if char in "\"'":
                quote = char
                i += 1
                while i < len(text):
                    if text[i] == quote and text[i - 1] != "\\":
                        break
                    i += 1

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
            if i + 1 < len(text) and text[i + 1] in ")]":
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

        elif char in "\"'":
            quote = char
            j = i + 1

            while j < len(text):
                if text[j] == quote and text[j - 1] != "\\":
                    break
                j += 1

            inner = text[i + 1 : j]

            if len(inner) > max_str_len:
                current += quote + "TOO LONG TO DISPLAY" + quote
            else:
                current += quote + inner + quote

            i = j

        else:
            current += char

        i += 1

    if current.strip():
        lines.append(" " * (indent * indent_size) + current.strip())

    return "\n".join(lines)

def pretty_object(obj, indent=0):
    representation = repr(obj)

    if len(representation) > 100_000:
        return (
            "# CUTOFF AFTER 100.000 CHARACTERS!\n\n"
            + format_repr(representation[:100_000], indent_size=4)
            + "\n#                 ... (truncated) ...\n\n\n"
        )
    return format_repr(representation, indent_size=4)
