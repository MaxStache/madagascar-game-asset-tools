"""Scratch driver for the tfbpseudo library.

Compiles `TfbPseudo.tai` into a script file and prints the decompilation of a
game script. Run it from the repo root: `uv run python tfbcompiler.py`.
"""

from pathlib import Path

from tfbpseudo import compile_source, decompile_script
from tfbscript.script import ScriptFile

SOURCE_PATH = Path("TfbPseudo.tai")
COMPILED_PATH = Path("compiled.out.ai")
DECOMPILE_PATH = Path("Levels/mutiny/553_ME_Toiletguys.ai")


def compile_file(source: Path, output: Path) -> ScriptFile:
    """Compile a TfbPseudo source file and write the script file to `output`."""
    script = compile_source(source.read_text())

    with output.open("wb") as f:
        script.write(f)

    return script


def decompile_file(path: Path) -> str:
    """Decompile an .ai file back into TfbPseudo source text."""
    return decompile_script(ScriptFile.from_path(path))


def main() -> None:
    compiled = compile_file(SOURCE_PATH, COMPILED_PATH)
    compiled.print_tree()

    decompiled = decompile_file(DECOMPILE_PATH)
    Path("decompiled.gig.txt").write_text(decompiled)
    #open_editor(ScriptFile.from_path(DECOMPILE_PATH))


if __name__ == "__main__":
    main()
