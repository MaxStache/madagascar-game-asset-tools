# pyright: basic

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import override

from tfbscript.opcodes.base import InstructionFlags, Opcode

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QRadioButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .search import ROW_PADDING, SearchEntry, row_text
from .style import Win98TreeStyle, tfb_colored_box


def clear_layout(layout: QHBoxLayout):
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()

def text_to_tb(label: QWidget):
    fm = label.fontMetrics()
    label.setFixedHeight(fm.height())

class RHSDialog(QDialog):
    def __init__(self, rhs=None, parent=None):
        super().__init__(parent)

        self.rhs = rhs

        self.setWindowTitle("RHS Builder")

        layout = QVBoxLayout(self)

        self.option1 = QRadioButton("Integer")
        self.option2 = QRadioButton("Float")
        self.option3 = QRadioButton("Color")
        self.option4 = QRadioButton("(X,Y) Position")
        self.option5 = QRadioButton("Reference")
        self.option6 = QRadioButton("Expression (Combination)")

        layout.addWidget(self.option1)
        layout.addWidget(self.option2)
        layout.addWidget(self.option3)
        layout.addWidget(self.option4)
        layout.addWidget(self.option5)
        layout.addWidget(self.option6)

        # Select the existing RHS kind
        if rhs is not None:
            options = {
                "int": self.option1,
                "float": self.option2,
                "color": self.option3,
                "pair": self.option4,
                "reference": self.option5,
                "expression": self.option6,
            }

            if button := options.get(rhs.kind):
                button.setChecked(True)

        buttons = QDialogButtonBox(
            standardButtons=(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

class RHSButton(QPushButton):
    doubleClicked = Signal()

    def __init__(self, rhs, parent=None):
        super().__init__(parent)
        self.rhs = rhs

    def mouseDoubleClickEvent(self, event):
        dialog = RHSDialog(self.rhs, self.window())

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rhs = dialog.rhs

        super().mouseDoubleClickEvent(event)

def opcode_row(opcode: Opcode, layout: QHBoxLayout, on_change: Callable[[], None]):
    fields = opcode.editor_repr().get("fields", [])

    for _field in fields:
        f_type = _field.get("type")

        if f_type == "op-label":
            label = QLabel(_field.get("value", ""))
            tfb_colored_box(label, "#0000AA")
            text_to_tb(label)
            layout.addWidget(label)

        elif f_type == "behavior-label":
            label = QLabel(_field.get("value", ""))
            tfb_colored_box(label, "#00AA31")
            text_to_tb(label)
            layout.addWidget(label)

        elif f_type == "block-label":
            label = QLabel(_field.get("value", ""))
            label.setStyleSheet("font-weight: bold;")
            text_to_tb(label)
            layout.addWidget(label)

        elif f_type == "label":
            label = QLabel(_field.get("content", ""))
            label.setStyleSheet("font-weight: bold;")
            text_to_tb(label)
            layout.addWidget(label)

        elif f_type == "string":
            label = QLabel(_field.get("value", ""))
            label.setStyleSheet("color: #8A8880;")
            text_to_tb(label)
            layout.addWidget(label)

        elif f_type == "rhs":
            selected = _field.get("rhs")
            attr_name = _field.get("name")

            button = RHSButton(selected, str(selected))
            text_to_tb(button)
            button.setFlat(True)
            button.setStyleSheet(
                "QPushButton { padding: 2px 4px; margin: 0px; border: none; background-color: #616161; color: #FFFFFF; }"
                " QPushButton::menu-indicator { image: none; width: 0px; height: 0px; }"
            )
            layout.addWidget(button)


        elif f_type == "ref":
            content = str(_field.get("ref", None))
            label = QLabel(content)
            tfb_colored_box(label, "#616161")
            text_to_tb(label)
            layout.addWidget(label)

        elif f_type == "flow":
            content = str(_field.get("value", None))
            label = QLabel(content)
            tfb_colored_box(label, "#616161")
            text_to_tb(label)
            layout.addWidget(label)

        elif f_type == "enum":
            selected = _field.get("entry", _field.get("value", None))
            attr_name = _field.get("name")

            button = QPushButton(str(selected))
            text_to_tb(button)
            button.setFlat(True)
            button.setStyleSheet(
                "QPushButton { padding: 2px 4px; margin: 0px; border: none; background-color: #616161; color: #FFFFFF; }"
                " QPushButton::menu-indicator { image: none; width: 0px; height: 0px; }"
            )
            layout.addWidget(button)
            menu = QMenu(button)
            menu.setStyleSheet(
                "QMenu { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; padding: 2px; }"
                " QMenu::item { padding: 4px 16px; }"
                " QMenu::item:selected { background-color: #5a5a5a; color: #ffffff; }"
            )

            def select_entry(entry: object, attr_name: str | None = attr_name) -> None:
                if attr_name is not None:
                    setattr(opcode, attr_name, entry)
                on_change()

            for entry in selected.__class__:
                action = menu.addAction(str(entry))
                action.triggered.connect(
                    lambda checked=False, entry=entry: select_entry(entry)
                )

            button.setMenu(menu)

        else:
            raise NotImplementedError(f"Unsupported field type: {f_type}")

@dataclass
class FlowControlOpcode(Opcode):
    parent_op_idx: int = field(default=-1)
    op_flags: InstructionFlags = field(default_factory=InstructionFlags)

    @override
    def editor_repr(self) -> dict:
        return {
            "fields": [
                {"type": "label", "content": "flow"},
                {"type": "label", "content": self.op_flags.flow_control_str()} if self.parent_op_idx == 0xFF else {"type": "flow", "value": self.op_flags.flow_control_str()},
            ]
        }


@dataclass
class GroupOpcode(Opcode):
    """Pseudo-opcode heading a labelled branch of another opcode's body, e.g.
    the "true" / "else" halves of an if/else. `scope` holds the opcodes that
    must stay open while its body renders (see ParserContext.open_opcodes)."""

    label: str = field(default="")
    scope: list[Opcode] = field(default_factory=list)

    @override
    def editor_repr(self) -> dict:
        return {
            "fields": [{"type": "label", "content": self.label}],
            "hasBody": True,
            "scope": self.scope,
        }


def populate_tree(
    parent: QTreeWidget | QTreeWidgetItem,
    opcode: Opcode,
    search_index: list[SearchEntry] | None = None,
):
    item = QTreeWidgetItem(parent)
    item.setExpanded(False)

    tree = item.treeWidget()

    editor_repr = opcode.editor_repr()
    # An opcode may render its row from another opcode ("row"), e.g. if/else
    # shows its condition, so edits land on the opcode the fields came from.
    row_opcode = editor_repr.get("row", opcode)

    container = QWidget()
    outer_layout = QHBoxLayout(container)
    outer_layout.setContentsMargins(Win98TreeStyle.CONTENT_OFFSET, 0, 0, 2)
    outer_layout.setSpacing(0)
    outer_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    # The fields live in their own widget so a row highlight can hug the
    # content instead of stretching across the full width of the tree. Its
    # margin is the padding around a highlight, and is reserved unconditionally
    # so switching the highlight on and off never nudges the row's contents.
    content = QWidget()
    layout = QHBoxLayout(content)
    layout.setContentsMargins(
        ROW_PADDING, ROW_PADDING, ROW_PADDING, ROW_PADDING
    )
    layout.setSpacing(4)
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    outer_layout.addWidget(content)
    outer_layout.addStretch()

    entry = SearchEntry(item=item, content=content)
    if search_index is not None:
        search_index.append(entry)

    def rerender_row() -> None:
        clear_layout(layout)
        opcode_row(row_opcode, layout, rerender_row)
        entry.set_text(row_text(layout))

    rerender_row()

    tree.setItemWidget(item, 0, container)
    context = opcode.context
    scope = [opcode, *editor_repr.get("scope", [])]
    if context is not None:
        context.open_opcodes.extend(scope)

    try:
        groups = editor_repr.get("groups")
        if groups is not None:
            # Each group becomes a labelled node owning part of the body; the
            # flow-control row is emitted per group, not for the opcode itself.
            for group in groups:
                populate_tree(
                    item,
                    GroupOpcode(
                        opcode_index=opcode.opcode_index,
                        flags=opcode.flags,
                        context=context,
                        children=list(group.get("children", [])),
                        label=group.get("label", ""),
                        scope=list(group.get("scope", [])),
                    ),
                    search_index,
                )
        elif opcode.children or editor_repr.get("hasBody", False):
            for child in opcode.children:
                populate_tree(item, child, search_index)
            populate_tree(
                item,
                FlowControlOpcode(
                    parent_op_idx=opcode.opcode_index, op_flags=opcode.flags
                ),
                search_index,
            )
    finally:
        if context is not None:
            del context.open_opcodes[-len(scope) :]
