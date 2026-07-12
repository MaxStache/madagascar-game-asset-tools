"""CLI entry point: ``python -m analyze [FILE]``."""

import argparse

from .app import run

# Previously hardcoded samples, kept for quick reference:
#   Levels/KingOfNY/170_marty.dff
#   Levels/KingOfNY-unchanged/92_TreasureDoor.dff
#   Levels/KingOfNY-unchanged/2_TD_LEVEL FOLDER.txd
#   Levels/KingOfNY/48_janitor_walk.anm
DEFAULT_FILE = "Levels/KingOfNY-unchanged/416_marty_jump.anm"


def main():
    ap = argparse.ArgumentParser(prog="analyze", description=__doc__)
    ap.add_argument(
        "file",
        nargs="?",
        default=DEFAULT_FILE,
        help=f"RenderWare file to open (default: {DEFAULT_FILE})",
    )
    args = ap.parse_args()
    run(args.file)


if __name__ == "__main__":
    main()
