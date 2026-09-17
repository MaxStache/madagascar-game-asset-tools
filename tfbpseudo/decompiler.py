"""Decompiler turning a `ScriptFile` back into TfbPseudo source text."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tfbpseudo.compiler import METHOD_OPCODE_TABLE
from tfbpseudo.errors import DecompileError
from tfbpseudo.lexer import Token, synth_token
from tfbpseudo.nodes import FLOW_CONTINUE, Block, Flow, Statement
from tfbpseudo.references import (
    BARE_NAME,
    BUILTIN_TOKEN_BY_KIND,
    INDEX_CLOSE,
    INDEX_OPEN,
    MEMBER_INDEX_WORD,
    MEMBER_OP,
    NULL_BUILTIN_TOKEN,
    SCOPE_INDEX_WORD,
    SCOPE_OP,
    SUB_INDEX_WORD,
    SUB_OP,
    TABLE_TOKEN_BY_KIND,
    find_entry,
    member_name,
)
from tfbpseudo.rhs import condition_tokens, rhs_tokens
from tfbscript import opcodes
from tfbscript.reference import Reference as TFBReference
from tfbscript.opcodes.enums import RelOp
from tfbscript.reference import SCOPE_LABELS, ReferenceType
from tfbscript.rhs import Rhs
from tfbscript.script import ScriptFile
from tfbscript.string_table import StringTableEntry

DecompileFn = Callable[[Any, "Decompiler"], Statement]


@dataclass(frozen=True)
class DecompileSpec:
    handler: DecompileFn
    method_name: str  # TfbPseudo method the statement calls, e.g. "createVariable"


OPCODE_DECOMPILE_TABLE: dict[type[opcodes.Opcode], DecompileSpec] = {}


def make_statement(
    method_name: str,
    arguments: list[list[Token]],
    block: Block | None = None,
) -> Statement:
    """Build the Statement for a call to `method_name`, checking it against the
    method's compile-side spec so the two directions cannot drift apart."""
    spec = METHOD_OPCODE_TABLE.get(method_name)
    if spec is None:
        raise DecompileError(f"no compile handler registered for `{method_name}`")

    if not spec.accepts(len(arguments)):
        raise DecompileError(
            f"`{method_name}` takes {spec.arity()} arguments, got {len(arguments)}"
        )

    return Statement(
        method=[synth_token("NAME", method_name)],
        arguments=arguments,
        block=block,
    )


def decompile_handler(opcode_type: type[opcodes.Opcode], method_name: str):
    """Register the handler that turns `opcode_type` instances back into a
    statement calling the TfbPseudo method `method_name`."""

    def register(fn: DecompileFn) -> DecompileFn:
        if method_name not in METHOD_OPCODE_TABLE:
            raise DecompileError(
                f"`{method_name}` has no compile handler to mirror, "
                + "register one with @opcode_handler first"
            )

        OPCODE_DECOMPILE_TABLE[opcode_type] = DecompileSpec(
            handler=fn, method_name=method_name
        )
        return fn

    return register


def flow_from_flags(flags: opcodes.InstructionFlags) -> Flow | None:
    """The trailing `flow` a block needs to compile back to these flags, or None
    when the opcode just continues and the block can stay silent about it."""
    if flags.flow_control == FLOW_CONTINUE:
        return None

    return Flow(value=flags.flow_control)


def render_token(token: Token) -> str:
    if token.kind == "STRING":
        escaped = token.value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    return token.value


# Punctuation that takes no space in front of it, and punctuation that takes
# none after: `color(255, 0, 0, 255)`, `@myself.waypoints#first:sub[0x01]`.
GLUE_BEFORE = frozenset({"(", ")", ",", MEMBER_OP, SCOPE_OP, SUB_OP, INDEX_OPEN, INDEX_CLOSE})
GLUE_AFTER = frozenset({"(", MEMBER_OP, SCOPE_OP, SUB_OP, INDEX_OPEN})


def render_argument(tokens: list[Token]) -> str:
    """Join an argument's tokens back into source. Everything is space
    separated, except the punctuation of a call or a reference chain."""
    out = ""
    previous = ""

    for token in tokens:
        text = render_token(token)
        glued = not out or text in GLUE_BEFORE or previous in GLUE_AFTER

        out += text if glued else f" {text}"
        previous = text

    return out


def name_tokens(name: str) -> list[Token]:
    """A field name as source: bare when the lexer reads it back as one name,
    quoted when it has punctuation in it, like "heading (OBSOLETE)"."""
    if BARE_NAME.fullmatch(name):
        return [synth_token("NAME", name)]

    return [synth_token("STRING", name)]


def field_tokens(type_name: str | None, index: int, index_word: str) -> list[Token]:
    """A field after a `.` or `:`, named when the type is known and the field
    has a name, and given by index when it is not."""
    name = member_name(type_name, index) if type_name is not None else None

    if name is not None:
        return name_tokens(name)

    return [
        synth_token("NAME", index_word),
        synth_token("OP", INDEX_OPEN),
        synth_token("NUMBER", f"{index:#04x}"),
        synth_token("OP", INDEX_CLOSE),
    ]


def render_statement_head(statement: Statement) -> str:
    method = " ".join(t.value for t in statement.method)
    arguments = ", ".join(render_argument(a) for a in statement.arguments)

    return f"{method}({arguments})"


class Decompiler:
    def __init__(self, script: ScriptFile):
        self.tfbscript = script
        self.script = None
        self.output = ""
        self.indentation_level = 0
        self.indent_size = 4

    def add_line(self, text: str = ""):
        indent = (self.indentation_level * self.indent_size) * " "
        self.output += indent + text + "\n"

    def decompile(self):
        self.output = "// THIS IS A DECOMPILATION AND MIGHT NOT BE 100% ACCURATE \n"
        self.add_line()

        # Globals
        self.add_line("globals {")
        self.indentation_level = 1

        for g in self.tfbscript.global_refs.entries:
            self.add_line(f"{render_token(synth_token('STRING', g.string))};")

        self.indentation_level = 0
        self.add_line("}")
        self.add_line()

        # Locals
        self.add_line("locals {")
        self.indentation_level = 1

        # A behavior with a block of its own is declared by that block. One
        # without -- scripts do declare behaviors they never implement -- has
        # to be declared here or the entry would be lost.
        implemented = {
            instruction.behavior_entry.string
            for instruction in self.tfbscript.instructions
            if isinstance(instruction, opcodes.OpBehaviorImplementation)
            and instruction.behavior_entry is not None
        }

        for g in self.tfbscript.local_refs.entries:
            if g.string == "my::actor":
                continue
            if g.type == "behavior" and g.category is None and g.string in implemented:
                continue

            self.add_line(f"{render_token(synth_token('STRING', g.string))};")

        self.indentation_level = 0
        self.add_line("}")
        self.add_line()

        # Prescript
        self.add_line("prescript {")
        self.indentation_level = 1

        prescript = next(
            (
                instruction
                for instruction in self.tfbscript.instructions
                if isinstance(instruction, opcodes.OpPrescript)
            ),
            None,
        )

        startup = self.prescript_child(prescript, opcodes.OpStartup)
        shutdown = self.prescript_child(prescript, opcodes.OpShutdown)

        self.add_line("startup {")
        self.indentation_level = 2
        if startup is not None:
            self.decompile_block(startup)
        self.indentation_level = 1
        self.add_line("}")
        self.add_line()

        self.add_line("shutdown {")
        self.indentation_level = 2
        if shutdown is not None:
            self.decompile_block(shutdown)
        self.indentation_level = 1
        self.add_line("}")
        self.add_line()

        self.add_line("update {")
        self.indentation_level = 2
        if prescript is not None:
            # Update has no opcode of its own: its statements are whatever the
            # prescript has besides startup and shutdown, and its `flow` is
            # what the prescript itself returns.
            self.emit_block(
                self.block_from_children(
                    prescript,
                    [
                        child
                        for child in prescript.children
                        if child is not startup and child is not shutdown
                    ],
                    flow_from_flags(prescript.flags),
                )
            )
        self.indentation_level = 1
        self.add_line("}")

        self.indentation_level = 0
        self.add_line("}")
        self.add_line()

        # BEHAVIORS
        for i in self.tfbscript.instructions:
            if isinstance(i, opcodes.OpBehaviorImplementation):
                if not i.behavior_entry:
                    raise DecompileError(
                        "OpBehaviorImplementation doesnt have a behavior entry, no name can be resolved"
                    )

                # The declaration names the behavior itself, so it is always
                # the bare name -- it is references to it that may need the
                # whole string to tell two same-named entries apart.
                name = render_argument(name_tokens(i.behavior_entry.name))
                self.add_line(f"behavior {name} {{")
                self.indentation_level = 1
                self.decompile_block(i)
                self.indentation_level = 0
                self.add_line("}")
                self.add_line()

        return self.output

    def prescript_child(
        self, prescript: opcodes.Opcode | None, opcode_type: type[opcodes.Opcode]
    ) -> opcodes.Opcode | None:
        """The prescript's `startup` or `shutdown` block, if it has one."""
        if prescript is None:
            return None

        return next(
            (
                child
                for child in prescript.children
                if isinstance(child, opcode_type)
            ),
            None,
        )

    def ref_tokens(self, ref: TFBReference) -> list[Token]:
        """The tokens a compile handler would have read `ref` from --
        the inverse of Compiler.read_ref."""
        # Null first: its member/scope/sub bits are all ones by definition, so
        # it has no chain to walk.
        if ref.kind == ReferenceType.NULL:
            return [synth_token("BUILTIN", NULL_BUILTIN_TOKEN)]

        tokens = self.ref_base_tokens(ref)

        if ref.member:
            tokens.append(synth_token("OP", MEMBER_OP))
            tokens += field_tokens(
                self.chain_type(ref, before_sub=False), ref.member, MEMBER_INDEX_WORD
            )

        if ref.scope:
            tokens += self.scope_tokens(ref)

        if ref.sub:
            tokens.append(synth_token("OP", SUB_OP))
            tokens += field_tokens(
                self.chain_type(ref, before_sub=True), ref.sub, SUB_INDEX_WORD
            )

        return tokens

    def ref_base_tokens(self, ref: TFBReference) -> list[Token]:
        """The target the chain starts at."""
        if ref.kind == ReferenceType.BUILTIN:
            if ref.builtin_kind is None:
                raise DecompileError("builtin reference has no builtin_kind")

            name = BUILTIN_TOKEN_BY_KIND.get(ref.builtin_kind)
            if name is None:
                raise DecompileError(
                    f"builtin {ref.builtin_kind.name} has no TfbPseudo spelling"
                )

            return [synth_token("BUILTIN", name)]

        if ref.kind in (ReferenceType.LOCAL, ReferenceType.GLOBAL):
            # Shipped scripts have variables called "interrupted?" and
            # "yes/no_current_selection_index", which only read back quoted.
            return self.variable_tokens(ref)

        raise DecompileError(f"Reference has unknown kind {ref.kind}")

    def variable_tokens(self, ref: TFBReference) -> list[Token]:
        """How to write the variable `ref` points at so that reading it back
        finds that very entry: its bare name if that is enough, otherwise the
        whole "name::category::type" string, and `@global` in front when a
        local of the same name would be found first.

        Both sides go through find_entry, so this asks what the compiler would
        do rather than guessing at the rule."""
        if ref.entry is None:
            raise DecompileError(
                f"{ref.kind.name.lower()} reference to slot {ref.slot} "
                + "does not resolve to a variable"
            )

        for name in (ref.entry.name, ref.entry.string):
            for table in (None, ref.kind):
                found = find_entry(
                    self.tfbscript.local_refs,
                    self.tfbscript.global_refs,
                    name,
                    table,
                )

                if found is not None and (found[0], found[1]) == (ref.kind, ref.slot):
                    tokens = name_tokens(name)
                    if table is None:
                        return tokens

                    return [synth_token("BUILTIN", TABLE_TOKEN_BY_KIND[table])] + tokens

        raise DecompileError(
            f"no way to write {ref.entry.string!r} so that it reads back as "
            + f"{ref.kind.name.lower()} slot {ref.slot}"
        )

    def variable_name(self, entry: StringTableEntry) -> str:
        """What to call `entry` where there is no reference to disambiguate
        with, which is the `locals` section and a behavior's own block."""
        return entry.name

    def scope_tokens(self, ref: TFBReference) -> list[Token]:
        """`#first` when the scope picks out of a set, which is the only
        meaning that is understood, and the raw `#scope[2]` otherwise -- the
        shipped scripts scope plain values too, and what that does is an open
        question (Reference.__str__ prints those as "@2")."""
        label = SCOPE_LABELS.get(ref.scope)

        try:
            picks_from_set = ref._selects_from_set()  # pyright: ignore[reportPrivateUsage]
        except ValueError:
            picks_from_set = False

        if label is not None and picks_from_set:
            return [synth_token("OP", SCOPE_OP), synth_token("NAME", label)]

        return [synth_token("OP", SCOPE_OP)] + [
            synth_token("NAME", SCOPE_INDEX_WORD),
            synth_token("OP", INDEX_OPEN),
            synth_token("NUMBER", str(ref.scope)),
            synth_token("OP", INDEX_CLOSE),
        ]

    def chain_type(self, ref: TFBReference, before_sub: bool) -> str | None:
        """The type a field index is named against, or None when it cannot be
        resolved -- mirrors Compiler._chain_type."""
        try:
            if before_sub:
                return ref.resolve_type(apply_sub=False).type

            return ref.get_resolved_type()
        except ValueError:
            return None

    def rhs_tokens(self, rhs: Rhs) -> list[Token]:
        """The tokens a compile handler would have read `rhs` from --
        the inverse of Compiler.get_rhs_by_tokens."""
        return rhs_tokens(rhs, self.ref_tokens)

    def condition_tokens(
        self, lhs: TFBReference, rel_op: RelOp, rhs: Rhs
    ) -> list[Token]:
        """The tokens a compile handler would have read this condition from --
        the inverse of Compiler.get_condition_by_tokens."""
        return condition_tokens(lhs, rel_op, rhs, self.ref_tokens)

    def statement_from_opcode(self, opcode: opcodes.Opcode) -> Statement:
        # if/else is not a method of its own: it is the wrapper a check gets
        # when it has an else, so it decompiles onto that check's statement.
        if isinstance(opcode, opcodes.OpIfElse):
            return self.statement_from_if_else(opcode)

        spec = OPCODE_DECOMPILE_TABLE.get(type(opcode))
        if spec is None:
            raise DecompileError(
                f"Unknown or Unimplemented opcode `{type(opcode).__name__}`!"
            )

        return spec.handler(opcode, self)

    def statement_from_if_else(self, opcode: opcodes.OpIfElse) -> Statement:
        """The check an if/else wraps, with the rest of the if/else's children
        as its else branch -- the inverse of Compiler.wrap_if_else."""
        if not opcode.children:
            raise DecompileError("if/else has no condition to decide on")

        condition = opcode.children[0]

        if isinstance(condition, opcodes.OpIfElse):
            # An if/else whose condition is another if/else would need two
            # else branches on one statement, and TfbPseudo has room for one.
            raise DecompileError(
                "if/else wraps another if/else, which TfbPseudo cannot spell "
                + "-- a statement carries a single else branch"
            )

        # The condition is read from inside the if/else, so anything in the
        # then branch can resolve through it.
        context = opcode.context
        if context is not None:
            context.open_opcodes.append(opcode)
        try:
            statement = self.statement_from_opcode(condition)
        finally:
            if context is not None:
                context.open_opcodes.pop()

        # The then branch lives in the condition's own children, so the
        # statement needs a body to hold it even when there is nothing in it:
        # `check(...) { } else { ... }` is a real shape.
        if statement.block is None:
            statement.block = self.block_from_opcode(condition)

        statement.else_block = self.block_from_children(
            opcode, opcode.children[1:], flow_from_flags(opcode.flags)
        )

        return statement

    def block_from_opcode(self, opcode: opcodes.Opcode) -> Block:
        """The Block of statements whose compilation are `opcode`'s children."""
        return self.block_from_children(
            opcode, opcode.children, flow_from_flags(opcode.flags)
        )

    def block_from_children(
        self,
        owner: opcodes.Opcode,
        children: list[opcodes.Opcode],
        flow: Flow | None,
    ) -> Block:
        """The Block `children` decompile to, read as the body of `owner`.
        Only `update` passes anything but all of the owner's children."""
        body: list[Statement | Token] = []

        # Stay "open" while the body is rendered, the protocol every traversal
        # that descends into children follows (see ParserContext.open_opcodes):
        # a builtin like `@controlled` resolves its type through the op that
        # produced it, which is one of the ops we are inside of right now.
        context = owner.context
        if context is not None:
            context.open_opcodes.append(owner)

        try:
            for child in children:
                if isinstance(child, opcodes.OpComment):
                    body.append(synth_token("COMMENT", f" {child.content}"))
                    continue

                try:
                    body.append(self.statement_from_opcode(child))
                except DecompileError as e:
                    # Keep going: one unimplemented opcode should not cost us
                    # the rest of the script, it just cannot be compiled back.
                    body.append(synth_token("COMMENT", f" !! {e}"))
        finally:
            if context is not None:
                context.open_opcodes.pop()

        return Block(body, flow)

    def decompile_block(self, opcode: opcodes.Opcode):
        self.emit_block(self.block_from_opcode(opcode))

    def emit_block(self, block: Block):
        for item in block.body:
            if isinstance(item, Token):
                self.add_line(f"//{item.value}")
            else:
                self.emit_statement(item)

        if block.flow is not None:
            self.add_line(block.flow.makeString())

    def emit_statement(self, statement: Statement):
        head = render_statement_head(statement)

        if statement.block is None:
            self.add_line(f"{head};")
            return

        self.add_line(f"{head} {{")
        self.indentation_level += 1
        self.emit_block(statement.block)
        self.indentation_level -= 1

        if statement.else_block is None:
            self.add_line("};")
            return

        self.add_line("} else {")
        self.indentation_level += 1
        self.emit_block(statement.else_block)
        self.indentation_level -= 1
        self.add_line("};")


def decompile_script(script: ScriptFile) -> str:
    """Decompile a script file into TfbPseudo source text."""
    return Decompiler(script).decompile()
