from dataclasses import dataclass
from typing import Any, BinaryIO, override

from tfbscript.ansi import flow_control, keyword
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.payload import PayloadReader


@opcode("if/else")
@dataclass
class OpIfElse(Opcode):
    # No payload of its own. The first child is the condition opcode; the
    # condition's own children are the "then" branch, and any remaining
    # children of the if/else are the "else" branch.

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpIfElse":
        return cls()

    @override
    def print_tree(self, indent: int = 0, chained: bool = False) -> None:
        if not self.children:
            return

        pad = "    " * indent
        condition = self.children[0]

        keyword_str = "} else if (" if chained else "if ("

        print(
            f"{pad}{keyword(keyword_str)} {condition.source_line(inline=True)} {keyword(') {')}"
        )

        context = self.context
        if context is not None:
            context.open_opcodes.append(self)
        try:
            if context is not None:
                context.open_opcodes.append(condition)
            try:
                for then_child in condition.children:
                    then_child.print_tree(indent + 1)
            finally:
                if context is not None:
                    context.open_opcodes.pop()

            print(
                f"{'    ' * (indent + 1)}{keyword('flow ')}{flow_control(self.flags.flow_control_str())}"
            )

            else_children = self.children[1:]

            # None
            if not else_children:
                print(pad + keyword("}"))
            # ELSE IF
            elif len(else_children) == 1 and isinstance(else_children[0], OpIfElse):
                fist_child = else_children[0]
                fist_child.print_tree(indent, chained=True)  # type: ignore
            # ELSE
            else:
                print(pad + keyword("} else {"))
                for else_child in else_children:
                    else_child.print_tree(indent + 1)

                print(
                    f"{'    ' * (indent + 1)}{keyword('flow ')}{flow_control(self.flags.flow_control_str())}"
                )

                print(pad + keyword("}"))
        finally:
            if context is not None:
                context.open_opcodes.pop()

    @override
    def editor_repr(self) -> dict[str, Any]:
        # The row is the condition itself; its body is the "true" branch and
        # the remaining children are the "else" branch.
        if not self.children:
            return {"fields": [{"type": "op-label", "value": "if/else"}]}

        condition = self.children[0]
        else_children = self.children[1:]

        groups: list[dict[str, Any]] = [
            {
                "label": "true",
                "children": condition.children,
                "scope": [condition],
            }
        ]

        if else_children:
            groups.append({"label": "else", "children": else_children})

        return {
            "row": condition,
            "groups": groups,
        }

    @override
    def write_payload(self, f: BinaryIO) -> None:
        # If/Else has no payload
        pass