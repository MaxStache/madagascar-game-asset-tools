"""Compiler turning a parsed TfbPseudo `Script` into a `ScriptFile`."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tfbpseudo.errors import CompileError
from tfbpseudo.lexer import Token, tokenize
from tfbpseudo.nodes import FLOW_CONTINUE, Block, Script, Statement, Variable
from tfbpseudo.parser import Parser
from tfbpseudo.references import (
    BUILTIN_TOKENS,
    FIELD_MAX,
    FIELD_MIN,
    INDEX_CLOSE,
    INDEX_OPEN,
    MEMBER_INDEX_WORD,
    MEMBER_OP,
    NULL_BUILTIN_TOKEN,
    SCOPE_BY_NAME,
    SCOPE_INDEX_WORD,
    SCOPE_MAX,
    SCOPE_MIN,
    SCOPE_OP,
    SET_CLOSE,
    SET_OPEN,
    SUB_INDEX_WORD,
    SUB_OP,
    TABLE_TOKENS,
    BuiltinScope,
    builtin_out_of_scope,
    field_names,
    find_entry,
    member_index,
    member_is_set,
    names_a_set,
)
from tfbpseudo.rhs import parse_condition, parse_rhs
from tfbscript import opcodes
from tfbscript.opcodes.base import ParserContext
from tfbscript.reference import Reference as TFBReference
from tfbscript.reference import ReferenceType
from tfbscript.opcodes.enums import RelOp
from tfbscript.rhs import Rhs
from tfbscript.script import ScriptFile
from tfbscript.string_table import StringTableEntry

if TYPE_CHECKING:
    from tfbpseudo.arguments import Argument

CONTROL_BLOCK_INDEX = 0xFF

# The wrapper an `else` compiles to, as the opcode table names it.
IF_ELSE_OP_NAME = "if/else"

HandlerFn = Callable[[int, Statement, "Compiler"], opcodes.Opcode]


@dataclass(frozen=True)
class MethodSpec:
    handler: HandlerFn
    op_name: str  # name in the script's opcode table, e.g. "check reference"
    arg_count: int  # the fewest arguments it takes
    max_args: int | None = None  # the most, when trailing ones are optional
    # What it takes, in order, for whoever wants to name the arguments:
    # errors count them, the editor completes them.
    arguments: tuple["Argument", ...] = ()

    def accepts(self, count: int) -> bool:
        return self.arg_count <= count <= (
            self.arg_count if self.max_args is None else self.max_args
        )

    def arity(self) -> str:
        """How many arguments it takes, for an error message."""
        most = self.arg_count if self.max_args is None else self.max_args
        if most == self.arg_count:
            return f"{self.arg_count}"

        return f"{self.arg_count} to {most}"


METHOD_OPCODE_TABLE: dict[str, MethodSpec] = {}


def opcode_handler(
    name: str,
    op_name: str,
    arg_count: int,
    max_args: int | None = None,
    arguments: tuple["Argument", ...] = (),
):
    """Register a handler for a TfbPseudo method under `name`, emitting the
    opcode that the opcode table calls `op_name`."""

    def register(fn: HandlerFn) -> HandlerFn:
        METHOD_OPCODE_TABLE[name] = MethodSpec(
            handler=fn,
            op_name=op_name,
            arg_count=arg_count,
            max_args=max_args,
            arguments=arguments,
        )
        return fn

    return register


def _at_op(tokens: list[Token], pos: int, value: str) -> bool:
    return pos < len(tokens) and tokens[pos].kind == "OP" and tokens[pos].value == value


def block_flow_control(block: Block | None) -> int:
    """The flow-control value the opcode owning `block` returns: whatever its
    trailing `flow` says, or continue when it has none."""
    if block is None or block.flow is None:
        return FLOW_CONTINUE

    return block.flow.value


class Compiler:
    def __init__(self, script: Script):
        self.script = script
        self.tfbscript = ScriptFile()

        # Every reference and opcode built here shares this, and the ops being
        # compiled into stay on its stack, so a builtin like `@each` can
        # resolve its type through the `for each` it is written inside of --
        # the same way reading a file does it.
        self.context = ParserContext(
            opcode_table=self.tfbscript.opcode_table,
            global_refs=self.tfbscript.global_refs,
            local_refs=self.tfbscript.local_refs,
        )

    def opcode_index(self, op_name: str) -> int:
        table = self.tfbscript.opcode_table
        string = f"{op_name}::op-code"

        for index, entry in enumerate(table.entries):
            if entry.string == string:
                return index

        if len(table.entries) >= CONTROL_BLOCK_INDEX:
            raise CompileError(
                f"script uses more than {CONTROL_BLOCK_INDEX} distinct opcodes, "
                + "which does not fit the u8 opcode index",
                0,
                0,
            )

        table.entries.append(StringTableEntry(string))
        return len(table.entries) - 1

    def get_ref_by_tokens(self, tokens: list[Token]) -> TFBReference:
        """The reference an argument's tokens name, all of them."""
        ref, pos = self.read_ref(tokens, 0)

        if pos < len(tokens):
            t = tokens[pos]
            raise CompileError(
                f"unexpected {t.value!r} after the reference", t.line, t.col
            )

        return ref

    def read_ref(self, tokens: list[Token], pos: int) -> tuple[TFBReference, int]:
        """Read one `target.member#scope:sub` chain starting at `pos`, and
        return it with the position just past it. Each step is optional, but
        they only come in this order -- it is the order the engine walks them,
        see Reference.resolve_type."""
        ref, pos = self.read_ref_base(tokens, pos)

        if _at_op(tokens, pos, MEMBER_OP):
            # A member is a field of the target's own type.
            ref.member, pos = self._read_field(
                tokens, pos, self._chain_type(ref, before_sub=False), MEMBER_INDEX_WORD
            )

        if _at_op(tokens, pos, SCOPE_OP):
            ref.scope, pos = self._read_scope(tokens, pos, ref)

        if _at_op(tokens, pos, SUB_OP):
            # A sub is a field of whatever the chain has reached by now, which
            # is the element `scope` picked when there was one.
            ref.sub, pos = self._read_field(
                tokens, pos, self._chain_type(ref, before_sub=True), SUB_INDEX_WORD
            )

        elif ref.scope and _at_op(tokens, pos, MEMBER_OP):
            t = tokens[pos]
            raise CompileError(
                f"{MEMBER_OP!r} takes a field of the whole set, and {SCOPE_OP} has "
                + f"already picked one element out of it -- use {SUB_OP!r} for a "
                + "field of that element",
                t.line,
                t.col,
            )

        return ref, pos

    def _else_branch_hint(self, scope: BuiltinScope) -> str:
        """The one place the scope error looks wrong: the `else` of the very
        check that would have produced the builtin. The else branch is not the
        check's body -- it is the if/else's -- and it runs when the check found
        nothing, so there is nothing to name there either."""
        if_else = self.context.nearest_ancestor(opcodes.OpIfElse)

        if (
            if_else is None
            or not if_else.children
            or not isinstance(if_else.children[0], scope.producers)
        ):
            return ""

        return " -- an `else` runs when the check failed, so it has none"

    def _chain_type(self, ref: TFBReference, before_sub: bool) -> str | None:
        """The type a field name is looked up against, or None when the script
        cannot tell -- a builtin resolves through the op that produced it, and
        that op may not be in the tree yet."""
        try:
            if before_sub:
                return ref.resolve_type(apply_sub=False).type

            return ref.get_resolved_type()
        except ValueError:
            return None

    def _picks_from_set(self, ref: TFBReference) -> bool | None:
        """Whether what a `#scope` would pick from is a set; None when unknown.
        Reference decides this for rendering, so ask it rather than repeating
        the rule here."""
        try:
            return ref._selects_from_set()  # pyright: ignore[reportPrivateUsage]
        except ValueError:
            return None

    def _read_scope(
        self, tokens: list[Token], pos: int, ref: TFBReference
    ) -> tuple[int, int]:
        t_op = tokens[pos]
        token = tokens[pos + 1] if pos + 1 < len(tokens) else None
        names = ", ".join(SCOPE_BY_NAME)

        # `#scope[2]` is the raw form: the shipped scripts scope things the
        # script cannot show to be sets -- `@message`, whose type is not
        # resolvable, and plain actor variables, where what the engine does
        # with it is not understood (Reference.__str__ prints those as "@2").
        # Writing the bits outright says "I mean exactly this" and skips the
        # set check that the named forms below insist on.
        if (
            token is not None
            and token.kind == "NAME"
            and token.value == SCOPE_INDEX_WORD
            and _at_op(tokens, pos + 2, INDEX_OPEN)
        ):
            return self._read_index(
                tokens, pos + 2, SCOPE_INDEX_WORD, SCOPE_MIN, SCOPE_MAX
            )

        if token is None or token.kind != "NAME" or token.value not in SCOPE_BY_NAME:
            raise CompileError(
                f"expected {names} or {SCOPE_INDEX_WORD}{INDEX_OPEN}1{INDEX_CLOSE} "
                + f"after {SCOPE_OP!r}",
                t_op.line,
                t_op.col,
            )

        # `#first` picks one element out of a set, so there has to be a set to
        # pick from -- a plain value has nothing to take a first of.
        picks_from_set = self._picks_from_set(ref)

        if picks_from_set is None:
            raise CompileError(
                "cannot tell whether this is a set at compile time, "
                + f"so {SCOPE_OP}{token.value} cannot be checked",
                token.line,
                token.col,
            )

        if not picks_from_set:
            raise CompileError(
                f"{SCOPE_OP}{token.value} picks an element out of a set, "
                + "but this is not a set",
                token.line,
                token.col,
            )

        return SCOPE_BY_NAME[token.value], pos + 2

    def _read_field(
        self, tokens: list[Token], pos: int, type_name: str | None, index_word: str
    ) -> tuple[int, int]:
        """A field after `.` or `:`: a name, a quoted name, a raw index like
        `field[0x2a]`, or -- for a field that holds a set -- a name in the
        brackets a set may be written in, `.[waypoints]`. `pos` is the
        operator; the returned position is just past the field."""
        t_op = tokens[pos]

        # `.[waypoints]` is `.waypoints` said out loud. The brackets come
        # before the name, which is what tells them from the `field[0x2a]`
        # index form, where they come after it.
        t_open = tokens[pos + 1] if _at_op(tokens, pos + 1, SET_OPEN) else None
        name_pos = pos + 2 if t_open is not None else pos + 1

        token = tokens[name_pos] if name_pos < len(tokens) else None

        if token is None:
            raise CompileError(
                f"expected a field after {t_op.value!r}", t_op.line, t_op.col
            )

        if (
            t_open is None
            and token.kind == "NAME"
            and token.value == index_word
            and _at_op(tokens, pos + 2, INDEX_OPEN)
        ):
            return self._read_index(tokens, pos + 2, index_word, FIELD_MIN, FIELD_MAX)

        if token.kind not in ("NAME", "STRING"):
            raise CompileError(
                f"{token.value!r} is not a field name, "
                + f"write a name or {index_word}[0x01]",
                token.line,
                token.col,
            )

        if type_name is None:
            raise CompileError(
                f"cannot tell what this refers to at compile time, "
                + f"so {token.value!r} cannot be looked up -- "
                + f"name the field by index instead, e.g. {index_word}[0x01]",
                token.line,
                token.col,
            )

        index = member_index(type_name, token.value)

        if index is None:
            known = field_names(type_name)
            detail = (
                f"{type_name} has no field named {token.value!r}"
                if known
                else f"{type_name} has no named fields"
            )
            raise CompileError(
                f"{detail}, write {index_word}[0x01] to pick one by index",
                token.line,
                token.col,
            )

        if t_open is None:
            return index, name_pos + 1

        if not _at_op(tokens, name_pos + 1, SET_CLOSE):
            t = tokens[name_pos + 1] if name_pos + 1 < len(tokens) else t_open
            raise CompileError(
                f"expected {SET_CLOSE!r} to close {SET_OPEN!r} around "
                + f"{token.value!r}",
                t.line,
                t.col,
            )

        if member_is_set(type_name, index) is False:
            raise CompileError(
                f"{SET_OPEN}{SET_CLOSE} says {token.value!r} is a set of things, "
                + f"and {type_name}'s {token.value!r} is a single thing",
                t_open.line,
                t_open.col,
            )

        return index, name_pos + 2

    def _read_index(
        self, tokens: list[Token], pos: int, index_word: str, low: int, high: int
    ) -> tuple[int, int]:
        """The `[0x2a]` of `field[0x2a]`, and the same for `sub` and `scope`.
        `pos` is the opening bracket."""
        t_open = tokens[pos]
        token = tokens[pos + 1] if pos + 1 < len(tokens) else None

        if token is None or token.kind != "NUMBER":
            raise CompileError(
                f"expected an index after {index_word}{INDEX_OPEN}",
                t_open.line,
                t_open.col,
            )

        try:
            index = int(token.value, 0)
        except ValueError:
            raise CompileError(
                f"{token.value!r} is not a whole index", token.line, token.col
            ) from None

        if not low <= index <= high:
            raise CompileError(
                f"{index_word} index {index:#04x} is outside {low:#04x}..{high:#04x}",
                token.line,
                token.col,
            )

        if not _at_op(tokens, pos + 2, INDEX_CLOSE):
            raise CompileError(
                f"expected {INDEX_CLOSE!r} after the index", token.line, token.col
            )

        return index, pos + 3

    def read_ref_base(self, tokens: list[Token], pos: int) -> tuple[TFBReference, int]:
        """The target a reference starts at, with the brackets a set may be
        written in: `players` and `[players]` are the same target."""
        if not _at_op(tokens, pos, SET_OPEN):
            return self.read_ref_target(tokens, pos)

        t_open = tokens[pos]
        ref, pos = self.read_ref_target(tokens, pos + 1)

        if not _at_op(tokens, pos, SET_CLOSE):
            t = tokens[pos] if pos < len(tokens) else t_open
            raise CompileError(
                f"expected {SET_CLOSE!r} to close {SET_OPEN!r} -- "
                + self._set_bracket_hint(tokens, pos),
                t.line,
                t.col,
            )

        # The brackets are decoration, but they do say something, so a value
        # written as a set is a mistake worth stopping at. Only what the script
        # can actually tell: `@found_variable` is whatever the lookup found.
        if names_a_set(ref) is False:
            raise CompileError(
                f"{SET_OPEN}{SET_CLOSE} says this is a set of things, "
                + "and this one is a single thing",
                t_open.line,
                t_open.col,
            )

        return ref, pos + 1

    def _set_bracket_hint(self, tokens: list[Token], pos: int) -> str:
        """Where the brackets should have gone, said in terms of what was
        written instead. They hug the name of the set, the way Reference
        prints one, so the rest of the chain stays outside them."""
        if _at_op(tokens, pos, MEMBER_OP) or _at_op(tokens, pos, SUB_OP):
            return (
                "a field of something gets its own brackets, so they go around "
                + f"the field: `@myself{MEMBER_OP}{SET_OPEN}clones{SET_CLOSE}`"
            )

        if _at_op(tokens, pos, SCOPE_OP):
            return (
                f"{SCOPE_OP}first picks one element out of the set, so it comes "
                + f"after them: `{SET_OPEN}players{SET_CLOSE}{SCOPE_OP}first`"
            )

        return f"they go around the name of the set: `{SET_OPEN}players{SET_CLOSE}`"

    def read_ref_target(self, tokens: list[Token], pos: int) -> tuple[TFBReference, int]:
        """The target itself: a builtin, or a variable name."""
        if pos >= len(tokens):
            t = tokens[-1] if tokens else Token("EOF", "", 0, 0)
            raise CompileError("expected a reference", t.line, t.col)

        t_base = tokens[pos]
        pos += 1

        # `@local` / `@global` pick the table for the name that follows.
        table = TABLE_TOKENS.get(t_base.value) if t_base.kind == "BUILTIN" else None
        if table is not None:
            if pos >= len(tokens) or tokens[pos].kind not in ("NAME", "STRING"):
                bracketed = _at_op(tokens, pos, SET_OPEN)
                raise CompileError(
                    f"expected a variable name after {t_base.value}"
                    + (
                        f" -- the brackets go around the whole target, "
                        + f"{SET_OPEN}{t_base.value} name{SET_CLOSE}"
                        if bracketed
                        else ""
                    ),
                    t_base.line,
                    t_base.col,
                )

            t_base = tokens[pos]
            pos += 1

        if t_base.kind == "BUILTIN":  # either null or a builtin
            if t_base.value == NULL_BUILTIN_TOKEN:
                return (
                    TFBReference(kind=ReferenceType.NULL, context=self.context),
                    pos,
                )
            else:
                builtin_kind = BUILTIN_TOKENS.get(t_base.value, None)
                if not builtin_kind:
                    raise CompileError(
                        f"Unknown builtin '{t_base.value}'", t_base.line, t_base.col
                    )

                out_of_scope = builtin_out_of_scope(builtin_kind, self.context)
                if out_of_scope is not None:
                    raise CompileError(
                        out_of_scope.message(t_base.value)
                        + self._else_branch_hint(out_of_scope),
                        t_base.line,
                        t_base.col,
                    )

                return (
                    TFBReference(
                        kind=ReferenceType.BUILTIN,
                        builtin_kind=builtin_kind,
                        context=self.context,
                    ),
                    pos,
                )

        elif t_base.kind in ("NAME", "STRING"):
            # Quoted, because not every variable name in the shipped scripts is
            # made of bare words -- "interrupted?", "Auto-Save".
            name = t_base.value

            found = find_entry(
                self.tfbscript.local_refs, self.tfbscript.global_refs, name, table
            )

            if found is None:
                raise CompileError(
                    f"Undefined variable {name}",
                    t_base.line,
                    t_base.col,
                )

            ref_type, ref_slot, resolved_var_entry = found

            return (
                TFBReference(
                    kind=ref_type,
                    entry=resolved_var_entry,
                    slot=ref_slot,
                    context=self.context,
                ),
                pos,
            )

        else:
            raise CompileError(
                f"Expected a builtin, a name or a quoted name for a reference, "
                + f"but got {t_base.kind}",
                t_base.line,
                t_base.col,
            )

    def get_rhs_by_tokens(self, tokens: list[Token]) -> Rhs:
        """The right-hand-side operand an argument's tokens spell out."""
        return parse_rhs(tokens, self.read_ref)

    def get_condition_by_tokens(
        self, tokens: list[Token]
    ) -> tuple[TFBReference, RelOp, Rhs]:
        """The `lhs <op> rhs` condition an argument's tokens spell out."""
        return parse_condition(tokens, self.read_ref)

    def compile(self) -> ScriptFile:
        tfbscript = self.tfbscript

        # ----- GLOBALS -----
        for g in self.script.globals:
            metadata = b"\x00\x00\x00\x00"
            string = g.makeString()
            tfbscript.global_refs.entries.append(StringTableEntry(string, metadata))

        # ----- LOCALS -----
        # Behaviors first, then the declared variables, then `my` -- the order
        # the shipped scripts are in.
        self.script.locals = (
            [
                Variable(name=b.name, type="behavior", scope="", line=0)
                for b in self.script.behaviors.values()
            ]
            + self.script.locals
            + [Variable(name="my", type="actor", scope="", line=0)]
        )

        for g in self.script.locals:
            metadata = b"\x00\x00\x00\x00"
            string = g.makeString()
            tfbscript.local_refs.entries.append(StringTableEntry(string, metadata))

        # ----- PRESCRIPT -----
        if self.script.prescript is None:
            raise CompileError("Script doesnt have a prescript block", 0, 0)

        i_prescript = opcodes.OpPrescript(CONTROL_BLOCK_INDEX)

        i_prescript.context = self.context
        i_prescript.flags.flow_control = FLOW_CONTINUE
        tfbscript.instructions.append(i_prescript)

        # Startup
        i_startup = opcodes.OpStartup(CONTROL_BLOCK_INDEX)
        i_startup.context = self.context
        i_startup.flags.flow_control = FLOW_CONTINUE
        i_prescript.children.append(i_startup)

        if self.script.prescript.startup:
            self.compile_block_into(i_startup, self.script.prescript.startup)

        # Shutdown
        i_shutdown = opcodes.OpShutdown(CONTROL_BLOCK_INDEX)
        i_shutdown.context = self.context
        i_shutdown.flags.flow_control = FLOW_CONTINUE
        i_prescript.children.append(i_shutdown)

        if self.script.prescript.shutdown:
            self.compile_block_into(i_shutdown, self.script.prescript.shutdown)

        # Update -- it has no opcode of its own: its statements are the
        # prescript's own children and its `flow` is what the prescript returns.
        if self.script.prescript.update:
            self.compile_block_into(i_prescript, self.script.prescript.update)

        # ---- BEHAVIOURS ----
        for b in self.script.behaviors.values():
            i_behavior = opcodes.OpBehaviorImplementation(CONTROL_BLOCK_INDEX)
            i_behavior.context = self.context
            tfbscript.instructions.append(i_behavior)

            # -- We do this so it can show the behavior without re-parsing the script
            i_behavior.behavior_entry = next(
                var for var in self.tfbscript.local_refs.entries if var.name == b.name
            )
            # --

            self.compile_block_into(i_behavior, b.body)

        # --------------------

        return tfbscript

    def compile_block(self, block: Block) -> list[opcodes.Opcode]:
        out: list[opcodes.Opcode] = []

        for i in block.body:
            if isinstance(i, Token):
                i_comment = opcodes.OpComment(self.opcode_index("comment:"))
                i_comment.context = self.context
                i_comment.content = i.value.removeprefix(" ")
                i_comment.flags.flow_control = FLOW_CONTINUE
                out.append(i_comment)

            else:  # otherwise its a statement
                method_name = i.method[-1].value
                spec = METHOD_OPCODE_TABLE.get(method_name)
                if spec is None:
                    raise CompileError(
                        f"Unknown or Unimplemented instruction `{method_name}`!",
                        i.method[-1].line,
                        i.method[-1].col,
                    )

                if not spec.accepts(len(i.arguments)):
                    raise CompileError(
                        f"`{method_name}` takes {spec.arity()} arguments, "
                        + f"got {len(i.arguments)}",
                        i.method[-1].line,
                        i.method[-1].col,
                    )

                final_i = spec.handler(self.opcode_index(spec.op_name), i, self)
                final_i.flags.flow_control = block_flow_control(i.block)

                if i.else_block is not None:
                    final_i = self.wrap_if_else(final_i, i.else_block)

                out.append(final_i)

        return out

    def wrap_if_else(self, condition: opcodes.Opcode, else_block: Block) -> opcodes.Opcode:
        """Put `condition` inside an if/else, which is how the format stores a
        check that has an else: the if/else holds the condition as its first
        child and the else branch as the rest, while the condition keeps the
        then branch as its own children.

        Each half keeps its own flow -- the condition's is the then branch's,
        the if/else's is the else branch's -- which is what the shipped scripts
        do, they differ often enough that one value could not stand for both."""
        i_ifelse = opcodes.OpIfElse(self.opcode_index(IF_ELSE_OP_NAME))
        i_ifelse.context = self.context

        i_ifelse.children.append(condition)

        self.context.open_opcodes.append(i_ifelse)
        try:
            i_ifelse.children.extend(self.compile_block(else_block))
        finally:
            self.context.open_opcodes.pop()

        i_ifelse.flags.flow_control = block_flow_control(else_block)

        return i_ifelse

    def compile_block_into(self, opcode: opcodes.Opcode, block: Block) -> None:
        """Compile `block` as `opcode`'s body: the statements become its children
        and the block's trailing `flow` is what `opcode` returns once they ran."""
        self.context.open_opcodes.append(opcode)
        try:
            opcode.children.extend(self.compile_block(block))
        finally:
            self.context.open_opcodes.pop()

        opcode.flags.flow_control = block_flow_control(block)


def compile_source(source: str) -> ScriptFile:
    """Compile TfbPseudo source text into a script file."""
    return Compiler(Parser(tokenize(source), source).parse()).compile()
