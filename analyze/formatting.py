"""Hex dumping and pretty-printing of parsed section objects."""

from analyze.theme import COLORS


def hexdump(widget, data, width=8, parse_end=0x0):
    lines = []

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

    if len(data) > 15_000:
        widget.insert("1.0", "")
        widget.insert("2.0", f"Data too long to display ({len(data)} bytes).")
        widget.insert("3.0", "Showing first 15,000 bytes:")
        widget.insert("4.0", "")
        data = data[:15_000]
        read_tagging_offset = 4

    for off in range(0, len(data), width):
        line = off // width + 1 + read_tagging_offset

        chunk = data[off : off + width]

        hex_part = 0

        chunk_blocks = [
            " ".join(f"{b:02X}" for b in chunk[i * 8 : (i + 1) * 8])
            for i in range(blocks_per_chunk)
        ]

        hex_part = "  ".join(chunk_blocks)

        hex_part = hex_part.ljust(width * 3 - 1)

        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)

        line_text = f"{off:08X}  {hex_part}  {ascii_part}\n"
        widget.insert(f"{line}.0", line_text)
        lines.append(line_text)

        widget.tag_add("hex_offset", f"{line}.0", f"{line}.8")

        end_written = len(line_text) - len(ascii_part)
        widget.tag_add("hex_not_read", f"{line}.10", f"{line}.{end_written + 10}")

        read_in_line = max(0, min(parse_end - off, len(chunk)))
        if read_in_line > 0:
            read_end_col = byte_col(read_in_line - 1) + 2
            widget.tag_add("hex_read", f"{line}.10", f"{line}.{read_end_col}")

        ascii_part_start = 8 + len("  ") + len(hex_part) + len("  ")
        widget.tag_add(
            "hex_ascii",
            f"{line}.{ascii_part_start}",
            f"{line}.{ascii_part_start + width}",
        )

    widget.tag_raise("hex_read")


def format_repr(text: str, indent_size: int = 4, max_str_len: int = 150) -> str:
    lines = []
    indent = 0

    current = ""
    i = 0

    while i < len(text):
        char = text[i]

        if char in "([":
            # Empty brackets stay inline
            if i + 1 < len(text) and text[i + 1] in ")]":
                current += char + text[i + 1]
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

            # Don't output yet, comma might follow

        elif char == ",":
            current += char
            lines.append(" " * (indent * indent_size) + current.strip())
            current = ""

        elif char in "\"'":
            quote = char
            # Find the matching closing quote (handle escaped quotes)
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

            i = j  # jump to closing quote

        else:
            current += char

        i += 1

    if current.strip():
        lines.append(" " * (indent * indent_size) + current.strip())

    return "\n".join(lines)


def pretty_object(obj, indent=0):
    representation = repr(obj)

    if len(representation) > 50_000:
        return (
            "# CUTOFF AFTER 50.000 CHARACTERS!\n\n"
            + format_repr(representation[:50_000], indent_size=4)
            + "\n#                 ... (truncated) ...\n\n\n"
        )
    return format_repr(representation, indent_size=4)
