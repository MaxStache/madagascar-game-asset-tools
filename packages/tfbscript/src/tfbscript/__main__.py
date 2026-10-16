"""CLI: decompile TFB script (.ai) files to pretty-printed pseudo-source.

Usage:
    python -m tfbscript example_scripts/Teleporter.ai
    python -m tfbscript --no-color example_scripts/*.ai
"""

import argparse
import sys

from tfbscript.ansi import disable_colors, enable_colors
from tfbscript.script import ScriptFile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tfbscript",
        description="Decompile TFB script (.ai) files to pretty-printed pseudo-source.",
    )
    parser.add_argument("files", nargs="+", help="one or more .ai script files")
    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI syntax coloring (auto-disabled when piped or NO_COLOR is set)",
    )
    color_group.add_argument(
        "--color",
        action="store_true",
        help="force ANSI syntax coloring even when piped",
    )
    args = parser.parse_args(argv)

    if args.no_color:
        disable_colors()
    elif args.color:
        enable_colors()

    status = 0
    for path in args.files:
        if len(args.files) > 1:
            print(f"===== {path} =====")
        try:
            ScriptFile.from_path(path).print_tree()
        except (OSError, ValueError) as error:
            print(f"{path}: {error}", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
