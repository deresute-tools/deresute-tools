from PyQt5.QtCore import QSize, Qt, QMimeData
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QListWidget, QWidget, QHBoxLayout, QVBoxLayout, QListWidgetItem, QLineEdit, QPushButton, \
    QApplication

from src.logic.profile import unit_storage
from settings import IMAGE_PATH64, IMAGE_PATH32, IMAGE_PATH
from src.db import db
from src.gui.viewmodels.utils import ImageWidget


class UnitCard(ImageWidget):
    def __init__(self, unit_widget, card_idx, color='black', size=64, *args, **kwargs):
        super(UnitCard, self).__init__(*args, **kwargs)
        self.set_padding(1)
        self.toggle_border(True, size)
        self.setAcceptDrops(True)
        self.unit_widget = unit_widget
        self.card_idx = card_idx
        self.color = color

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.unit_widget.set_card(self.card_idx, None)
        elif event.button() == Qt.LeftButton:
            event.ignore()

    def dragEnterEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        try:
            card_id = int(e.mimeData().text())
        except ValueError:
            return
        self.unit_widget.set_card(self.card_idx, card_id)


class UnitWidget(QWidget):
    def __init__(self, unit_view, parent=None, size=64):
        super(UnitWidget, self).__init__(parent)
        self.unit_view = unit_view
        self.cards = list()
        self.card_ids = [None] * 6
        for idx in range(6):
            if idx == 0:
                color = 'red'
            elif idx == 5:
                color = 'blue'
            else:
                color = 'black'
            card = UnitCard(unit_widget=self, card_idx=idx, size=size, color=color)
            self.cards.append(card)
        self.unitName = QLineEdit()
        self.unitName.setMinimumSize(QSize(0, 15))
        self.unitName.setMaximumSize(QSize(16777215, 25))
        self.unitName.setMaxLength(80)
        self.size = size
        if self.size == 32:
            self.path = IMAGE_PATH32
        elif self.size == 64:
            self.path = IMAGE_PATH64
        elif self.size == 124:
            self.path = IMAGE_PATH

    def set_unit_name(self, unit_name):
        self.unitName.setText(unit_name)

    def set_card(self, idx, card_id):
        self.card_ids[idx] = card_id
        if card_id is None:
            self.cards[idx].set_path(None)
        else:
            self.cards[idx].set_path(str(self.path / "{:06d}.jpg".format(card_id)))
        self.cards[idx].repaint()
        if type(self) == UnitWidget:
            self.update_unit()

    def set_widget_item(self, widget_item):
        self.widget_item = widget_item

    def update_unit(self):
        unit_name = self.unitName.text().strip()
        card_ids = self.card_ids
        if unit_name != "":
            unit_storage.update_unit(unit_name=unit_name, cards=card_ids, grand=False)

    def delete_unit(self):
        unit_name = self.unitName.text().strip()
        if unit_name != "":
            unit_storage.delete_unit(unit_name)
        self.unit_view.delete_unit(self.widget_item)


class SmallUnitWidget(UnitWidget):
    def __init__(self, unit_view, parent=None):
        super(SmallUnitWidget, self).__init__(unit_view, parent)

        self.verticalLayout = QVBoxLayout()
        self.unitManagementLayout = QHBoxLayout()

        self.unitName.editingFinished.connect(lambda: self.update_unit())

        self.unitManagementLayout.addWidget(self.unitName)

        self.deleteButton = QPushButton()
        self.deleteButton.setText("Delete unit")
        self.deleteButton.clicked.connect(lambda: self.delete_unit())
        self.unitManagementLayout.addWidget(self.deleteButton)

        self.verticalLayout.addLayout(self.unitManagementLayout)
        self.cardLayout = QHBoxLayout()

        for card in self.cards:
            card.setMinimumSize(QSize(self.size + 2, self.size + 2))
            self.cardLayout.addWidget(card)

        self.verticalLayout.addLayout(self.cardLayout)
        self.setLayout(self.verticalLayout)


class DragableUnitList(QListWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.setDragEnabled(True)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.selected = self.selectedItems()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        if self.selectedItems():
            self.selected = self.selectedItems()
        if not self.selected:
            return
        drag = QDrag(self)
        mimedata = QMimeData()
        mimedata.setText(str(self.itemWidget(self.selected[0]).card_ids))
        drag.setMimeData(mimedata)
        drag.exec_(Qt.CopyAction | Qt.MoveAction)


class UnitView:
    def __init__(self, main):
        self.widget = DragableUnitList(main)
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.pics = None

    def set_model(self, model):
        self.model = model

    def load_data(self, data):
        for unit_name, unit_cards in data:
            myQCustomQWidget = SmallUnitWidget(self, self.widget)
            myQCustomQWidget.set_unit_name(unit_name)
            cards = unit_cards.split(",")
            for idx, card in enumerate(cards):
                if card == "":
                    continue
                myQCustomQWidget.set_card(idx, int(card))
            myQListWidgetItem = QListWidgetItem(self.widget)
            myQCustomQWidget.set_widget_item(myQListWidgetItem)
            myQListWidgetItem.setSizeHint(myQCustomQWidget.sizeHint())
            self.widget.addItem(myQListWidgetItem)
            self.widget.setItemWidget(myQListWidgetItem, myQCustomQWidget)

    def add_empty_widget(self):
        unit_widget = SmallUnitWidget(self, self.widget)
        unit_widget_item = QListWidgetItem(self.widget)
        unit_widget.set_widget_item(unit_widget_item)
        unit_widget_item.setSizeHint(unit_widget.sizeHint())
        self.widget.addItem(unit_widget_item)
        self.widget.setItemWidget(unit_widget_item, unit_widget)

    def delete_unit(self, unit_widget):
        self.widget.takeItem(self.widget.row(unit_widget))

    def __del__(self):
        unit_storage.clean_all_units(grand=False)
        for r_idx in range(self.widget.count()):
            widget = self.widget.itemWidget(self.widget.item(r_idx))
            widget.update_unit()


class UnitModel:

    def __init__(self, view):
        self.view = view
        self.images = dict()

    def initialize_units(self):
        data = db.cachedb.execute_and_fetchall("SELECT unit_name, cards FROM personal_units WHERE grand = 0")
        self.view.load_data(data)
