"""The syntax tree a TfbPseudo source file parses into."""

from dataclasses import dataclass, field

from tfbpseudo.lexer import Token


# Flow-control values, as stored in InstructionFlags.flow_control (3 bits).
FLOW_END = 0
FLOW_CONTINUE = 1
FLOW_BREAK_BASE = 1  # `flow break n` is stored as n + FLOW_BREAK_BASE
FLOW_MAX = 7


@dataclass
class Flow:
    """A block's trailing `flow ...`, the flow-control value the opcode owning
    the block returns once the block is done."""

    value: int  # 0 end, 1 continue, 2 and up break
    line: int = 0
    col: int = 0

    def makeString(self) -> str:
        """Mirrors InstructionFlags.flow_control_str, in TfbPseudo spelling."""
        if self.value == FLOW_END:
            return "flow end"

        if self.value == FLOW_CONTINUE:
            return "flow continue"

        return f"flow break {self.value - FLOW_BREAK_BASE}"


@dataclass
class Block:
    body: list["Statement | Token"]
    flow: Flow | None = None  # at most one, and only at the end of the block


@dataclass
class Statement:
    method: list[Token]
    arguments: list[list[Token]]
    block: Block | None = None
    else_block: Block | None = None  # only a check can have one
    comments: list[Token] = field(default_factory=list)  # found inside the arg list


@dataclass
class Variable:
    name: str
    scope: str
    type: str
    line: int

    def makeString(self) -> str:
        out = self.name

        if self.scope != "":
            out += f"::{self.scope}"

        out += f"::{self.type}"

        return out


@dataclass
class Prescript:
    startup: Block | None = None
    shutdown: Block | None = None
    update: Block | None = None


@dataclass
class Behavior:
    name: str
    body: Block


@dataclass
class Script:
    globals: list[Variable] = field(default_factory=list)
    locals: list[Variable] = field(default_factory=list)
    prescript: Prescript | None = None
    behaviors: dict[str, Behavior] = field(default_factory=dict)
