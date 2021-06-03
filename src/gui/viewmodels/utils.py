import uuid

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath
from PyQt5.QtWidgets import QWidget, QTableWidgetItem
from numpy import int32


class ImageWidget(QWidget):

    def __init__(self, path=None, parent=None, card_idx=None):
        super(ImageWidget, self).__init__(parent)
        self.set_path(path)
        self.set_padding()
        self.border = False
        self.border_length = 0
        self.color = 'black'
        self.card_idx = card_idx

    def set_path(self, path):
        if path is None:
            self.picture = QPixmap(0, 0)
        else:
            self.picture = QPixmap(str(path))

    def toggle_border(self, value=False, border_length=0):
        self.border = value
        self.border_length = border_length + 1

    def set_padding(self, padding=5):
        self.padding = padding

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.border:
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, self.border_length, self.border_length), int(self.border_length // 16),
                                int(self.border_length // 16))
            color = QColor(self.color)
            painter.setPen(QPen(color))
            painter.drawPath(path)
            color.setAlpha(40)
            painter.fillPath(path, color)
        painter.drawPixmap(self.padding, self.padding, self.picture)


class NumericalTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        if isinstance(value, int) or isinstance(value, float) or isinstance(value, int32):
            self.number = value
        QTableWidgetItem.__init__(self, str(value))

    def __lt__(self, other):
        if not isinstance(other, NumericalTableWidgetItem):
            comparatee = 0
        else:
            comparatee = other.number
        return self.number < comparatee

    def setData(self, p_int, Any, class_type=int):
        super().setData(p_int, Any)
        try:
            class_type(Any)
        except ValueError:
            return
        self.number = class_type(Any)


class ValidatableNumericalTableWidgetItem(NumericalTableWidgetItem):
    def __init__(self, value, validator, class_type):
        super().__init__(value)
        self.validator = validator
        self.class_type = class_type

    def setData(self, p_int, Any):
        passed = False
        try:
            self.class_type(Any)
            passed = True
        except:
            pass
        if passed and self.validator(self.class_type(Any)):
            super().setData(p_int, Any, self.class_type)
        else:
            super().setData(p_int, self.number, self.class_type)


class UniversalUniqueIdentifiable:
    def __init__(self):
        self.__uuid = uuid.uuid4().hex

    def get_uuid(self):
        return self.__uuid

    def get_short_uuid(self):
        return self.__uuid[:6]
