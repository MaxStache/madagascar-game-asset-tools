# pyright: basic

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle, QStyleOption, QWidget

BG = QColor("#DCDCDC")
TEXT = QColor("#101010")


def tfb_colored_box(element: QWidget, color: str):
    element.setStyleSheet(
        f"background-color: {color}; color: #FFFFFF; padding: 0px 4px;"
    )


def build_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, BG)
    palette.setColor(QPalette.ColorRole.WindowText, TEXT)
    palette.setColor(QPalette.ColorRole.Base, BG)
    palette.setColor(QPalette.ColorRole.AlternateBase, BG.lighter(105))
    palette.setColor(QPalette.ColorRole.ToolTipBase, BG)
    palette.setColor(QPalette.ColorRole.ToolTipText, TEXT)
    palette.setColor(QPalette.ColorRole.Text, TEXT)
    palette.setColor(QPalette.ColorRole.Button, BG)
    palette.setColor(QPalette.ColorRole.ButtonText, TEXT)
    palette.setColor(QPalette.ColorRole.BrightText, QColor("red"))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))

    # Disabled state, so grayed-out buttons/labels don't go invisible
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#707070")
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#707070")
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#707070")
    )

    return palette


class Win98TreeStyle(QProxyStyle):
    """Redraws QTreeView branch connectors as classic Win98/comctl32-style
    dotted lines and a dotted-bordered +/- box, instead of Fusion's arrows."""

    LINE_COLOR = QColor("#97A1AD")
    BOX_SIZE = 11

    CONTENT_OFFSET = 0

    BOX_INSET = 20

    def drawPrimitive(
        self,
        element: QStyle.PrimitiveElement,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None = None,
    ) -> None:
        if element == QStyle.PrimitiveElement.PE_IndicatorBranch:
            self._draw_branch(option, painter)
            return
        super().drawPrimitive(element, option, painter, widget)

    def _draw_branch(self, option: QStyleOption, painter: QPainter) -> None:
        rect = option.rect
        mid_x = max(rect.left(), rect.right() - self.BOX_INSET)
        mid_y = rect.center().y()
        state = option.state

        has_children = bool(state & QStyle.StateFlag.State_Children)
        has_sibling = bool(state & QStyle.StateFlag.State_Sibling)
        is_item = bool(state & QStyle.StateFlag.State_Item)
        is_open = bool(state & QStyle.StateFlag.State_Open)

        painter.save()
        pen = QPen(self.LINE_COLOR)
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)

        if has_sibling:
            painter.drawLine(
                mid_x + self.CONTENT_OFFSET,
                rect.top(),
                mid_x + self.CONTENT_OFFSET,
                rect.bottom(),
            )
        elif is_item:
            painter.drawLine(
                mid_x + self.CONTENT_OFFSET,
                rect.top(),
                mid_x + self.CONTENT_OFFSET,
                mid_y,
            )

        # Horizontal line
        if is_item:
            painter.drawLine(
                mid_x + self.CONTENT_OFFSET,
                mid_y,
                rect.right() + self.CONTENT_OFFSET,
                mid_y,
            )

        painter.restore()

        if has_children:
            box_size = max(7, min(self.BOX_SIZE, rect.width() - 2, rect.height() - 2))
            if box_size % 2 == 0:
                box_size -= 1
            half = box_size // 2

            box_x = mid_x - half
            box_y = mid_y - half
            box = QRect(box_x, box_y, box_size, box_size)

            painter.save()
            painter.setPen(QPen(QColor("#788897"))) # BOX BORDER COLOR
            painter.setBrush(QColor("#DCDCDC")) # BOX BG COLOR
            painter.drawRect(box)

            painter.setPen(QPen(QColor("#3F3F3F"))) # SIGN COLOR

            # + or - sign
            sign_x = mid_x + self.CONTENT_OFFSET
            painter.drawLine(box.left() + 2, box_y + half, box.right() - 2, box_y + half) # -
            if not is_open: # |  (| + - = +)
                painter.drawLine(
                    sign_x,
                    box.top() + 2,
                    sign_x,
                    box.bottom() - 2,
                )

            painter.restore()
