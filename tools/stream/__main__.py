"""CLI entry point: ``python -m stream [FILE]``."""

import argparse

from .app import run

DEFAULT_FILE = "kingofny.stream"

def main():
    ap = argparse.ArgumentParser(prog="analyze", description=__doc__)
    ap.add_argument(
        "file",
        nargs="?",
        default=DEFAULT_FILE,
        help=f"RenderWare Studio Stream (.stream) file to open (default: {DEFAULT_FILE})",
    )
    args = ap.parse_args()
    run(args.file)


if __name__ == "__main__":
    main()
