"""Compare two TFB script (.ai) files and report exactly which instructions differ.

Usage:
    python diff_ai.py old.ai new.ai
    python diff_ai.py old.ai new.ai --bytes --depth 1
    python diff_ai.py old.ai new.ai --no-tables --quiet

The two scripts are parsed, their instruction trees are matched level by level
(so an inserted instruction shifts everything below it instead of reporting the
whole rest of the file as changed), and every difference is printed as one of:

    +   an instruction (with its subtree) only present in the new file
    -   an instruction (with its subtree) only present in the old file
    ~   an instruction present in both, but with different parameters or flags

Exit status is 0 when the two scripts are equivalent and 1 when they differ, so
it can be used like `diff` in shell scripts.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from tfbscript.ansi import colors_enabled, disable_colors, enable_colors
from tfbscript.opcodes import Opcode
from tfbscript.script import ScriptFile
from tfbscript.string_table import StringTable

_RESET = "\033[0m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_DIM = "\033[2m"
_BOLD = "\033[1m"


def _paint(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}" if colors_enabled() else text


# --------------------------------------------------------------------------- #
# Instruction tree -> comparable nodes
# --------------------------------------------------------------------------- #


@dataclass
class Node:
    """One instruction, rendered and keyed for comparison."""

    op: Opcode
    kind: str  # opcode class name, e.g. "OpMoveTo"
    text: str  # decompiled source line, without ANSI colors
    flow: str  # flow-control word ("end" / "continue" / "break N")
    no_handler: bool
    index: int  # position within its parent's child list
    children: list[Node] = field(default_factory=list)
    signature: str = ""  # deep structural key: identity + params + subtree


def _safe_source_line(op: Opcode) -> str:
    """`op.source_line()`, never raising -- a script that only half-decompiles
    should still diff on everything else."""
    try:
        return op.source_line()
    except Exception as error:  # noqa: BLE001
        return f"<unrenderable {type(op).__name__}: {error}>"


def _build(op: Opcode, index: int) -> Node:
    """Wrap one instruction (and its descendants) into a Node.

    Mirrors `Opcode.print_tree`'s push/pop of `context.open_opcodes` so that
    references resolving against an enclosing opcode (`[~each]`, `[~subset]`,
    ...) render the same text they would when printing the script.
    """
    node = Node(
        op=op,
        kind=type(op).__name__,
        text=_safe_source_line(op),
        flow=op.flags.flow_control_str(),
        no_handler=op.flags.no_handler,
        index=index,
    )

    if op.children:
        context = op.context
        if context is not None:
            context.open_opcodes.append(op)
        try:
            node.children = [_build(child, i) for i, child in enumerate(op.children)]
        finally:
            if context is not None:
                context.open_opcodes.pop()

    child_signatures = "".join(f"({child.signature})" for child in node.children)
    node.signature = (
        f"{node.kind}|{node.text}|{node.flow}|{int(node.no_handler)}|{child_signatures}"
    )
    return node


def build_tree(script: ScriptFile) -> list[Node]:
    """The script's whole instruction tree, as comparable nodes."""
    return [_build(op, i) for i, op in enumerate(script.instructions)]


def _subtree_size(node: Node) -> int:
    return 1 + sum(_subtree_size(child) for child in node.children)


# --------------------------------------------------------------------------- #
# Diffing
# --------------------------------------------------------------------------- #


class Report:
    """Collects differences in script order, then prints them."""

    def __init__(self, *, show_bytes: bool, max_depth: int | None) -> None:
        self.show_bytes = show_bytes
        self.max_depth = max_depth
        self.added = 0
        self.removed = 0
        self.modified = 0
        self._lines: list[str] = []

    # -- emitting ----------------------------------------------------------- #

    def _emit(self, text: str = "") -> None:
        self._lines.append(text)

    def _subtree(self, node: Node, marker: str, code: str, depth: int = 0) -> None:
        if self.max_depth is not None and depth > self.max_depth:
            if depth == self.max_depth + 1:
                self._emit(_paint(f"    {marker} {'  ' * depth}...", code))
            return
        self._emit(_paint(f"    {marker} {'  ' * depth}{node.text}", code))
        for child in node.children:
            self._subtree(child, marker, code, depth + 1)

    def node_added(self, node: Node, path: str) -> None:
        self.added += _subtree_size(node)
        self._emit(_paint(f"+ added   {path}#{node.index} (new file)", _GREEN + _BOLD))
        self._subtree(node, "+", _GREEN)
        self._emit()

    def node_removed(self, node: Node, path: str) -> None:
        self.removed += _subtree_size(node)
        self._emit(_paint(f"- removed {path}#{node.index} (old file)", _RED + _BOLD))
        self._subtree(node, "-", _RED)
        self._emit()

    def node_modified(
        self, old: Node, new: Node, path: str, details: list[str]
    ) -> None:
        self.modified += 1
        position = (
            f"#{old.index}"
            if old.index == new.index
            else f"#{old.index} -> #{new.index}"
        )
        self._emit(_paint(f"~ changed {path}{position}", _YELLOW + _BOLD))
        for detail in details:
            self._emit(f"    {detail}")
        self._emit()

    # -- output ------------------------------------------------------------- #

    def print(self) -> None:
        for line in self._lines:
            print(line)

    @property
    def total(self) -> int:
        return self.added + self.removed + self.modified


def _describe_change(old: Node, new: Node, show_bytes: bool) -> list[str]:
    """Detail lines for two instructions matched to the same slot. Empty when
    they are equivalent."""
    details: list[str] = []

    if old.kind != new.kind or old.text != new.text:
        details.append(_paint(f"- {old.text}", _RED))
        details.append(_paint(f"+ {new.text}", _GREEN))
    if old.flow != new.flow:
        details.append(_paint(f"~ flow: {old.flow} -> {new.flow}", _YELLOW))
    if old.no_handler != new.no_handler:
        details.append(
            _paint(f"~ no_handler: {old.no_handler} -> {new.no_handler}", _YELLOW)
        )
    if show_bytes and old.op.raw_payload != new.op.raw_payload:
        details.append(
            _paint(
                f"~ payload: {old.op.raw_payload.hex() or '-'}"
                + f" -> {new.op.raw_payload.hex() or '-'}",
                _DIM,
            )
        )
    return details


def _compare_pair(old: Node, new: Node, path: str, report: Report) -> None:
    """Compare two instructions matched to the same slot, then their children."""
    details = _describe_change(old, new, report.show_bytes)
    if details:
        report.node_modified(old, new, path, details)

    diff_levels(old.children, new.children, f"{path}#{old.index} {old.text} > ", report)


def diff_levels(
    old_nodes: list[Node], new_nodes: list[Node], path: str, report: Report
) -> None:
    """Align two sibling lists and report their differences."""
    matcher = SequenceMatcher(
        a=[node.signature for node in old_nodes],
        b=[node.signature for node in new_nodes],
        autojunk=False,
    )

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            if report.show_bytes:
                # Identical decompilation can still come from different bytes
                # (a re-encoded payload); only worth walking when asked for.
                for old, new in zip(old_nodes[i1:i2], new_nodes[j1:j2]):
                    _compare_pair(old, new, path, report)
        elif tag == "delete":
            for node in old_nodes[i1:i2]:
                report.node_removed(node, path)
        elif tag == "insert":
            for node in new_nodes[j1:j2]:
                report.node_added(node, path)
        else:  # "replace"
            _diff_replace_block(old_nodes[i1:i2], new_nodes[j1:j2], path, report)


def _diff_replace_block(
    old_nodes: list[Node], new_nodes: list[Node], path: str, report: Report
) -> None:
    """Re-align a replaced run on opcode identity alone, so an edited parameter
    reads as one change instead of a removal plus an addition."""
    matcher = SequenceMatcher(
        a=[node.kind for node in old_nodes],
        b=[node.kind for node in new_nodes],
        autojunk=False,
    )

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "delete":
            for node in old_nodes[i1:i2]:
                report.node_removed(node, path)
        elif tag == "insert":
            for node in new_nodes[j1:j2]:
                report.node_added(node, path)
        else:  # "equal" or "replace": pair up slot by slot
            olds, news = old_nodes[i1:i2], new_nodes[j1:j2]
            paired = min(len(olds), len(news))
            for old, new in zip(olds[:paired], news[:paired]):
                if old.kind == new.kind:
                    _compare_pair(old, new, path, report)
                else:
                    report.node_removed(old, path)
                    report.node_added(new, path)
            for node in olds[paired:]:
                report.node_removed(node, path)
            for node in news[paired:]:
                report.node_added(node, path)


# --------------------------------------------------------------------------- #
# Header / string-table diffing
# --------------------------------------------------------------------------- #


def diff_string_table(name: str, old: StringTable, new: StringTable) -> list[str]:
    """Report entries added to, removed from, or reordered within a string table."""
    old_strings = [entry.string for entry in old.entries]
    new_strings = [entry.string for entry in new.entries]
    if old_strings == new_strings:
        return []

    lines: list[str] = []

    if sorted(old_strings) == sorted(new_strings):
        lines.append(
            _paint(f"~ {name}: same {len(old_strings)} entries, reordered", _YELLOW)
        )
        for index, (old_string, new_string) in enumerate(zip(old_strings, new_strings)):
            if old_string != new_string:
                lines.append(
                    f"    [{index}] {_paint(old_string, _RED)}"
                    f" -> {_paint(new_string, _GREEN)}"
                )
        return lines

    lines.append(_paint(f"~ {name}:", _YELLOW))
    matcher = SequenceMatcher(a=old_strings, b=new_strings, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        for index, value in enumerate(old_strings[i1:i2], start=i1):
            lines.append(_paint(f"    - [{index}] {value}", _RED))
        for index, value in enumerate(new_strings[j1:j2], start=j1):
            lines.append(_paint(f"    + [{index}] {value}", _GREEN))
    return lines


def diff_header(old: ScriptFile, new: ScriptFile) -> list[str]:
    """Report differences in the file header and the three string tables."""
    lines: list[str] = []
    if old.magic_string != new.magic_string:
        lines.append(
            _paint(f"~ magic: {old.magic_string!r} -> {new.magic_string!r}", _YELLOW)
        )
    if old.unk != new.unk:
        lines.append(
            _paint(f"~ header bytes: {old.unk.hex()} -> {new.unk.hex()}", _YELLOW)
        )

    lines += diff_string_table("opcode table", old.opcode_table, new.opcode_table)
    lines += diff_string_table("global references", old.global_refs, new.global_refs)
    lines += diff_string_table("local references", old.local_refs, new.local_refs)
    return lines


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="diff_ai",
        description="Compare two TFB script (.ai) files instruction by instruction.",
    )
    parser.add_argument("old", help="the original .ai file")
    parser.add_argument("new", help="the modified .ai file")
    parser.add_argument(
        "--bytes",
        action="store_true",
        help="also report raw payload differences between instructions that "
        "decompile identically",
    )
    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="skip the header and string-table comparison, diff instructions only",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        metavar="N",
        help="when printing an added or removed instruction, show at most N "
        "levels of its children",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print nothing, only set the exit status",
    )
    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument(
        "--no-color", action="store_true", help="disable colored output"
    )
    color_group.add_argument(
        "--color", action="store_true", help="force colored output even when piped"
    )
    args = parser.parse_args(argv)

    if args.no_color or args.quiet:
        disable_colors()
    elif args.color:
        enable_colors()

    try:
        old_script = ScriptFile.from_path(Path(args.old))
        new_script = ScriptFile.from_path(Path(args.new))
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    header_lines = [] if args.no_tables else diff_header(old_script, new_script)

    report = Report(show_bytes=args.bytes, max_depth=args.depth)
    diff_levels(build_tree(old_script), build_tree(new_script), "", report)

    if args.quiet:
        return 1 if (header_lines or report.total) else 0

    print(_paint(f"--- {args.old}", _RED))
    print(_paint(f"+++ {args.new}", _GREEN))
    print()

    if header_lines:
        print(_paint("Header / string tables", _BOLD))
        for line in header_lines:
            print(line)
        print()

    if report.total:
        print(_paint("Instructions", _BOLD))
        print()
        report.print()
        print(
            f"{report.added} instruction(s) added, "
            f"{report.removed} removed, "
            f"{report.modified} changed."
        )
    elif header_lines:
        print("No instruction differences.")
    else:
        print("The two scripts are identical.")

    return 1 if (header_lines or report.total) else 0


if __name__ == "__main__":
    sys.exit(main())
