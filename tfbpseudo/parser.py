"""Parser turning a token stream into a `Script`."""

import re

from tfbpseudo.errors import ParseError
from tfbpseudo.lexer import Token
from tfbpseudo.nodes import (
    FLOW_BREAK_BASE,
    FLOW_CONTINUE,
    FLOW_END,
    FLOW_MAX,
    Behavior,
    Block,
    Flow,
    Prescript,
    Script,
    Statement,
    Variable,
)


class Parser:
    def __init__(self, tokens: list[Token], src: str):
        self.toks = tokens
        self.src = src
        self.pos = 0

    def peek(self) -> Token:
        return self.toks[self.pos]

    def next(self) -> Token:
        tok = self.toks[self.pos]
        self.pos += 1
        return tok

    def check(self, kind: str, value: str | None = None):
        t = self.peek()
        return t.kind == kind and (value is None or t.value == value)

    def at_flow(self) -> bool:
        """`flow end` and friends, as opposed to a call to a method named flow."""
        if not self.check("IDENT", "flow"):
            return False

        after = self.toks[self.pos + 1]
        return not (after.kind == "OP" and after.value == "(")

    def expect(self, kind: str, value: str | None = None):
        if not self.check(kind, value):
            t = self.peek()
            want = repr(value) if value else kind
            got = repr(t.value) if t.value else t.kind
            raise ParseError(f"expected {want}, got {got}", t.line, t.col)
        return self.next()

    def parse_name(self) -> Token:
        """A name are one or more words in one line: "My Variable" -> one NAME token."""
        first = self.expect("IDENT")
        last = first

        while (
            self.check("IDENT") or self.check("NUMBER")
        ) and self.peek().line == last.line:
            last = self.next()

        return Token(
            "NAME",
            self.src[first.pos : last.end],
            first.line,
            first.col,
            first.pos,
            last.end,
        )

    def parse(self):
        script = Script()

        while not self.check("EOF"):
            if self.check("IDENT"):
                t = self.expect("IDENT")
            elif self.check("COMMENT"):
                t = self.expect("COMMENT")
            else:
                raise SyntaxError(
                    f"Expected IDENT or COMMENT, got {self.peek().kind} ( {self.peek()!s} )"
                )

            if t.kind == "COMMENT":
                # SKIP COMMENT IN TOP LEVEL
                pass

            elif t.kind == "IDENT":
                if t.value == "globals":
                    script.globals += self.parse_var_section()
                elif t.value == "locals":
                    script.locals += self.parse_var_section()
                elif t.value == "prescript":
                    script.prescript = self.parse_prescript()

                elif t.value == "behavior":
                    # Quoted when the name is not made of bare words.
                    if self.check("STRING"):
                        name = self.next().value
                    else:
                        name = self.parse_name().value
                    if name in script.behaviors:
                        raise ParseError(
                            f"behavior with name {name} is defined multiple times",
                            t.line,
                            t.col,
                        )

                    script.behaviors[name] = Behavior(name, self.parse_block())

                else:
                    raise ParseError(
                        f"unknown top-level construct {t.value!r}", t.line, t.col
                    )

        return script

    def parse_prescript(self):
        self.expect("OP", "{")

        subblocks: dict[str, Block] = {}
        while not self.check("OP", "}"):
            t = self.expect("IDENT")
            if t.value not in ("startup", "update", "shutdown"):
                raise ParseError(
                    f"unknown prescript sub-block {t.value!r}", t.line, t.col
                )
            if t.value in subblocks:
                raise ParseError(f"duplicate sub-block {t.value!r}", t.line, t.col)

            subblocks[t.value] = self.parse_block()

        self.expect("OP", "}")

        return Prescript(**subblocks)

    def parse_statement(self) -> Statement | None:
        if self.check("OP", "}"):
            return None

        if self.check("EOF"):
            t = self.peek()
            raise ParseError("unexpected end of file", t.line, t.col)

        method: list[Token] = [self.parse_name()]

        # Kept because it is what an unclosed call has to be reported at: the
        # end of the file is where reading stops, not where the mistake is.
        opening = self.expect("OP", "(")

        arguments: list[list[Token]] = []
        current: list[Token] = []
        comments: list[Token] = []

        # Arguments are split on the commas of this call only: a nested call
        # like `color(255, 0, 0, 255)` keeps its own commas and parentheses.
        depth = 0

        while not self.check("EOF"):
            if self.check("OP", ")"):
                if depth == 0:
                    self.next()

                    if current:
                        arguments.append(current)

                    break

                depth -= 1
                current.append(self.next())
                continue

            if self.check("OP", "("):
                depth += 1
                current.append(self.next())
                continue

            if self.check("OP", ",") and depth == 0:
                self.next()
                arguments.append(current)
                current = []
                continue

            if self.check("IDENT"):
                current.append(self.parse_name())
                continue

            current.append(self.next())

        else:
            raise ParseError(
                f"unterminated `{method[0].value}(`",
                opening.line,
                opening.col,
            )

        block = None
        if self.check("OP", "{"):
            block = self.parse_block()

        # `else` hangs off the body, so there has to be a body to hang it on.
        else_block = None
        if block is not None and self.check("IDENT", "else"):
            self.next()
            else_block = self.parse_block()

        self.expect("OP", ";")

        return Statement(
            method=method,
            arguments=arguments,
            comments=comments,
            block=block,
            else_block=else_block,
        )

    def parse_flow(self) -> Flow:
        """`flow end`, `flow continue` or `flow break N` (N counts the levels to
        skip, default 1). The trailing semicolon is optional."""
        keyword = self.expect("IDENT", "flow")
        mode = self.expect("IDENT")

        if mode.value == "end":
            value = FLOW_END

        elif mode.value == "continue":
            value = FLOW_CONTINUE

        elif mode.value == "break":
            levels = 1

            if self.check("NUMBER") and self.peek().line == mode.line:
                t_levels = self.next()
                try:
                    levels = int(t_levels.value, 0)
                except ValueError:
                    raise ParseError(
                        f"flow break takes a whole number of levels, got {t_levels.value!r}",
                        t_levels.line,
                        t_levels.col,
                    ) from None

                if levels < 1:
                    raise ParseError(
                        "flow break skips at least 1 level, "
                        + "write `flow continue` to just carry on",
                        t_levels.line,
                        t_levels.col,
                    )

            value = levels + FLOW_BREAK_BASE

        else:
            raise ParseError(
                f"unknown flow control {mode.value!r}, "
                + "expected `end`, `continue` or `break`",
                mode.line,
                mode.col,
            )

        if value > FLOW_MAX:
            raise ParseError(
                f"flow break {value - FLOW_BREAK_BASE} does not fit the 3-bit "
                + f"flow-control field, at most `flow break {FLOW_MAX - FLOW_BREAK_BASE}`",
                keyword.line,
                keyword.col,
            )

        if self.check("OP", ";"):
            self.next()

        return Flow(value=value, line=keyword.line, col=keyword.col)

    def parse_block(self):
        opening = self.expect("OP", "{")

        body: list[Statement | Token] = []
        flow: Flow | None = None

        # Where the statement a comment could still be trailing sits, and the
        # line it ended on.
        open_statement: int | None = None
        open_statement_line = 0

        while not self.check("OP", "}"):
            if self.check("EOF"):
                raise ParseError(
                    "unterminated block", opening.line, opening.col
                )

            # Comments and empty statements carry no code, but comments are kept
            if self.check("COMMENT"):
                t_comment = self.next()

                # A comment trailing a statement is about that statement, so it
                # goes in front of it -- a block is a flat list of instructions
                # and that is the only way to keep the two together.
                if open_statement is not None and t_comment.line == open_statement_line:
                    body.insert(open_statement, t_comment)
                else:
                    body.append(t_comment)

                open_statement = None
                continue

            if self.check("OP", ";"):
                self.next()
                continue

            if self.at_flow():
                flow = self.parse_flow()

                # A block returns one flow-control value, once it is done, so
                # there is room for exactly one `flow` and only at the end.
                if not self.check("OP", "}"):
                    t = self.peek()
                    raise ParseError(
                        "`flow` has to be the last thing in its block, "
                        + "and a block can only have one",
                        t.line,
                        t.col,
                    )

                continue

            statement = self.parse_statement()

            if statement is not None:
                open_statement = len(body)
                open_statement_line = self.toks[self.pos - 1].line  # its ";"
                body.append(statement)

        self.expect("OP", "}")

        return Block(body, flow)

    def parse_variable_definition(self) -> Variable:
        var_tok = self.expect("STRING")

        split_var_parts = re.split(r"::(?!:)", var_tok.value)

        name: str = split_var_parts[0]
        category: str = split_var_parts[-2] if len(split_var_parts) > 2 else ""
        type: str = split_var_parts[-1]

        line = var_tok.line

        return Variable(name=name, scope=category, type=type, line=line)

    def parse_var_section(self):
        self.expect("OP", "{")

        vars: list[Variable] = []
        while not self.check("OP", "}"):
            var = self.parse_variable_definition()

            vars.append(var)
            self.expect("OP", ";")

        self.expect("OP", "}")

        return vars
