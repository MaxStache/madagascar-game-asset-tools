"""Launcher for the TfbPseudo text editor.

    uv run python tfbeditor.py                 empty editor
    uv run python tfbeditor.py TfbPseudo.tai   open a source file
    uv run python tfbeditor.py some.ai         decompile a script into it
"""

from tfbpseudo.editor import main

if __name__ == "__main__":
    main()
