"""CLI entry point: ``python -m tools.txd [FILE]``."""

import argparse

from .app import run


def main():
    ap = argparse.ArgumentParser(prog="txd", description=__doc__)
    ap.add_argument(
        "file",
        nargs="?",
        help=(
            "Texture dictionary (.txd), or a .stream to view the dictionaries "
            "embedded in it. Omit to pick one in a dialog."
        ),
    )
    args = ap.parse_args()
    run(args.file)


if __name__ == "__main__":
    main()
