"""The panel under the editor: tabs for what the editor has to say back.

Problems is the script compiled as it is typed, after a moment's quiet. The
compiler stops at the first thing it cannot read, so finding the next one
means blanking the line that one is on and compiling again -- which is what
`check` does, as far as it can be pushed. An empty list means the text
compiles, which is the half of the answer you otherwise only get by asking.

Problems also carries the warnings: the things that compile and are still
worth saying, which the compiler has no reason to mention.

Output is the running log of what the window has done: what it opened, saved
and compiled, kept where the status bar cannot keep it. A compile or a
decompile writes the whole of `describe` there -- what came out the other
end, in as much detail as the script itself can answer for.
"""

# pyright: basic

import io
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QTabWidget,
)

from tfbpseudo.compiler import compile_source
from tfbpseudo.editor.completions import DECLARATION_BLOCK, QUOTED, variables
from tfbpseudo.editor.theme import DEFAULT, Theme
from tfbpseudo.editor.widgets import CodeEditor
from tfbpseudo.errors import CompileError, DecompileError, ParseError
from tfbscript import opcodes
from tfbscript.opcodes.base import Opcode
from tfbscript.script import ScriptFile

HEIGHT = 200  # what the panel opens at, before anyone drags it
QUIET = 300  # milliseconds of no typing before the text is compiled again
MOST = 10  # problems to look for, each one costing another compile
TOP = 6  # opcodes named in the "most of" line of a report

# `createVariable(my timer)`, however it is spaced, and quoted or not.
CREATED = re.compile(r"""createVariable\s*\(\s*"?([^)"]*)"?\s*\)""")


@dataclass(frozen=True)
class Problem:
    """Something the compiler will not accept, and where it is."""

    message: str  # already spelled the way the errors spell themselves
    line: int = 0  # 0 when the error carries no position to jump to
    col: int = 0
    warning: bool = False  # said, but not in the way of a compile

    def colour(self, theme: Theme) -> str:
        return theme.warning if self.warning else theme.unknown_method


def first_problem(source: str) -> Problem | None:
    """Compile `source` without writing anything, for what it stops at."""
    try:
        compile_source(source)
    except (ParseError, CompileError, DecompileError) as error:
        return Problem(str(error), error.line, error.col)
    except SyntaxError as error:
        # The lexer and the parser raise these with the position written into
        # the message rather than carried beside it.
        return Problem(str(error))
    except Exception as error:  # a bug, but not one worth losing the text over  # noqa: BLE001
        return Problem(f"{type(error).__name__}: {error}")

    return None


def check(source: str) -> list[Problem]:
    """Everything wrong with `source` that can be found one compile at a time.

    The compiler stops at the first thing it cannot read, so the way on is to
    blank the line it stopped on and ask again -- blank rather than commented
    out, because a comment is not allowed everywhere a statement is, and the
    line numbers under everything below have to stay put.

    A line with a brace on it is left alone and ends the search: taking one
    out would unbalance the blocks, and every problem after that would be
    invented rather than found.
    """
    lines = source.splitlines()
    found: list[Problem] = []
    blanked: set[int] = set()

    while len(found) < MOST:
        problem = first_problem("\n".join(lines))
        if problem is None:
            break

        if problem.line in blanked:
            # Blanking that line moved the complaint rather than settling it,
            # so what comes back now is the same problem wearing a new hat.
            break

        found.append(problem)
        index = problem.line - 1

        if not 0 <= index < len(lines):
            break  # nothing to move past: the error carries no position
        if "{" in lines[index] or "}" in lines[index]:
            break

        blanked.add(problem.line)
        lines[index] = ""

    # In the order they are read, not the order they were found: a parse error
    # comes out of the whole file before any of the rest are looked for.
    return sorted(found, key=lambda problem: (problem.line, problem.col))


def mentioned(name: str, text: str) -> bool:
    """Whether `name` appears in `text` as a name, not inside a longer one.

    Not a word boundary at both ends: a name is allowed to end in punctuation
    -- the shipped scripts have a `sound played?` -- and a boundary after a
    "?" is not where anyone would think it is.
    """
    word = "[A-Za-z0-9_]"
    before = f"(?<!{word})" if re.match(word, name[:1]) else ""
    after = f"(?!{word})" if re.match(word, name[-1:]) else ""

    return re.search(before + re.escape(name) + after, text) is not None


def warned(variable, message: str) -> Problem:
    """A warning about `variable`, written the way an error writes itself."""
    return Problem(
        f"[Ln {variable.line}] {message}", variable.line, 1, warning=True
    )


def warnings(source: str) -> list[Problem]:
    """What compiles and is still worth saying.

    Three things the compiler has no reason to mind: a variable declared and
    never mentioned again, the same name declared twice, and a `user` local
    nothing ever creates -- which reads as zero in the game rather than as the
    mistake it is. Only a local: a global belongs to the level, and whoever
    owns it is free to be another script entirely.

    Behaviors are left out of the unused check: a behavior can be entered by
    something other than this script's own setBehavior, so a quiet one is not
    evidence of anything.
    """
    declared = variables(source)
    body = DECLARATION_BLOCK.sub("", source)
    created = {match.group(1).strip() for match in CREATED.finditer(source)}

    counted = Counter(
        entry.group(1).split("::")[0].strip()
        for block in DECLARATION_BLOCK.finditer(source)
        for entry in QUOTED.finditer(block.group(2))
    )

    found: list[Problem] = []

    for variable in declared:
        if counted[variable.name] > 1:
            found.append(warned(variable, f"{variable.name} is declared twice"))

        if variable.type == "behavior":
            continue

        if not mentioned(variable.name, body):
            found.append(
                warned(variable, f"{variable.name} is declared but never used")
            )
        elif (
            variable.scope == "local"
            and variable.category == "user"
            and variable.name not in created
        ):
            found.append(
                warned(
                    variable,
                    f"{variable.name} is a user variable that nothing creates, "
                    "add createVariable for it",
                )
            )

    return found


# ----- what there is to say about a compiled script -----


def walk(instructions: Iterable[Opcode]) -> Iterator[Opcode]:
    """Every instruction in the tree, the blocks and what is inside them."""
    for instruction in instructions:
        yield instruction
        yield from walk(instruction.children)


def opcode_name(instruction: Opcode) -> str | None:
    """What the script's own opcode table calls `instruction`.

    None for a block that is not an opcode at all -- a prescript, a behavior,
    an if/else -- which is written with an index no table entry answers to.
    """
    entries = instruction.context.opcode_table.entries if instruction.context else []
    if 0 <= instruction.opcode_index < len(entries):
        return entries[instruction.opcode_index].name

    return None


def kinds(entries) -> str:
    """The types in a string table, counted: "4 value, 2 sound, 1 camera"."""
    counted = Counter(
        f"set of {entry.type}" if entry.category == "set" else entry.type
        for entry in entries
    )
    return ", ".join(f"{count} {kind}" for kind, count in counted.most_common())


def written_size(script: ScriptFile) -> int:
    """How many bytes the script comes to, without writing a file to find out."""
    buffer = io.BytesIO()
    script.write(buffer)
    return buffer.tell()


def describe(script: ScriptFile) -> list[str]:
    """What `script` is made of, a line at a time.

    Everything here is read back off the compiled script rather than off the
    text it came from, so it says what was actually built -- which is the
    point of asking after a compile.
    """
    instructions = list(walk(script.instructions))
    counted = Counter(
        name for instruction in instructions if (name := opcode_name(instruction))
    )
    behaviors = [
        instruction.behavior_entry.name
        for instruction in script.instructions
        if isinstance(instruction, opcodes.OpBehaviorImplementation)
        and instruction.behavior_entry is not None
    ]

    lines = [
        f"{len(instructions)} instructions, "
        f"{len(script.opcode_table.entries)} opcodes in the table, "
        f"{written_size(script)} bytes",
        f"{len(script.global_refs.entries)} globals: "
        f"{kinds(script.global_refs.entries) or 'none'}",
        f"{len(script.local_refs.entries)} locals: "
        f"{kinds(script.local_refs.entries) or 'none'}",
    ]

    if behaviors:
        lines.append(f"{len(behaviors)} behaviors: " + ", ".join(behaviors))

    if counted:
        lines.append(
            "most of: "
            + ", ".join(f"{name} x{count}" for name, count in counted.most_common(TOP))
        )

    return lines


def style_sheet(theme: Theme) -> str:
    return f"""
    QTabWidget::pane {{
        background: {theme.base};
        border: 1px solid {theme.border};
    }}
    QTabBar::tab {{
        background: {theme.window};
        color: {theme.disabled};
        border: 1px solid transparent;
        padding: 3px 10px;
    }}
    QTabBar::tab:selected {{
        background: {theme.base};
        color: {theme.text};
        border-color: {theme.border};
        border-bottom-color: {theme.base};
    }}
    QTabBar::tab:hover {{ color: {theme.text}; }}
    QListWidget, QPlainTextEdit {{
        background: {theme.base};
        color: {theme.text};
        border: none;
    }}
    QListWidget::item {{ padding: 2px 4px; }}
    QListWidget::item:selected {{
        background: {theme.selection};
        color: {theme.selected_text};
    }}
    """


class Panel(QTabWidget):
    """The tabs under the editor, and the compile that feeds the first one."""

    def __init__(self, editor: CodeEditor, theme: Theme = DEFAULT):
        super().__init__()
        self.editor = editor
        self.theme = theme

        # No font of its own: the panel is chrome, so it reads in the window's
        # font. The fixed one belongs to the text being edited.
        self.problems = QListWidget(self)
        self.problems.itemActivated.connect(self.jump)
        self.problems.itemClicked.connect(self.jump)

        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)

        self.addTab(self.problems, "Problems")
        self.addTab(self.output, "Output")

        # Typing is what runs the check, but not every keystroke: a compile in
        # the middle of a half-written line only ever says the same thing.
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(QUIET)
        self.timer.timeout.connect(self.lint)
        editor.document().contentsChanged.connect(self.timer.start)

        self.set_theme(theme)
        self.lint()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.setStyleSheet(style_sheet(theme))
        self.lint()  # the rows are coloured, so they have to be made again

    # ----- the check -----

    def lint(self) -> None:
        """Compile what is in the editor and show what it said."""
        source = self.editor.toPlainText()
        found = sorted(
            check(source) + warnings(source),
            key=lambda problem: (problem.line, problem.col),
        )

        self.problems.clear()
        for problem in found:
            item = QListWidgetItem(problem.message)
            item.setForeground(QColor(problem.colour(self.theme)))
            item.setData(Qt.ItemDataRole.UserRole, (problem.line, problem.col))
            self.problems.addItem(item)

        self.setTabText(
            self.indexOf(self.problems),
            f"Problems ({len(found)})" if found else "Problems",
        )

        # Tinted, never jumped to: they are lines being typed in. Only what
        # stops a compile is tinted -- a warning is not worth colouring a line
        # you are working on.
        self.editor.mark_errors(
            problem.line
            for problem in found
            if problem.line and not problem.warning
        )

    def jump(self, item: QListWidgetItem) -> None:
        """Put the cursor where the problem is, when it says where that is."""
        line, col = item.data(Qt.ItemDataRole.UserRole)
        if line:
            self.editor.show_error_at(line, col)
            self.editor.setFocus()

    # ----- the log -----

    def log(self, message: str) -> None:
        self.output.appendPlainText(message)

    def report(self, title: str, lines: Iterable[str]) -> None:
        """A heading and what it has to say, and Output brought to the front.

        Only ever for something that was asked for -- a compile, an open --
        never for the check that runs on its own while typing.
        """
        self.log(f"--- {title} ---")
        for line in lines:
            self.log(f"    {line}")

        self.setCurrentWidget(self.output)
