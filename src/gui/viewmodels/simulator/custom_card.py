from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QAbstractItemView

from src.gui.viewmodels.utils import NumericalTableWidgetItem
from src.static.color import Color


class CustomCardView:
    def __init__(self, main):
        self.widget = QtWidgets.QTableWidget(main)
        self.widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.widget.setSortingEnabled(False)
        self.widget.verticalHeader().setVisible(True)
        self.widget.horizontalHeader().setVisible(False)
        self.widget.setRowCount(7)
        self.widget.setColumnCount(1)
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.horizontalHeader().setSectionResizeMode(1)  # Not allow change icon column size
        self.widget.setVerticalHeaderLabels(["Color", "Vocal", "Dance", "Visual", "Life", "Skill Duration", "Skill Interval"])

    def set_model(self, model):
        self.model = model

    def set_values(self, values):
        self.disconnect_cell_changed()
        if len(values) != 7:
            return
        for _ in range(7):
            self.widget.setItem(_, 0, NumericalTableWidgetItem(values[_]))
        self.connect_cell_changed()

    def connect_cell_changed(self):
        self.widget.cellChanged.connect(lambda r, c: self.model.handle_cell_change(r))

    def disconnect_cell_changed(self):
        try:
            self.widget.cellChanged.disconnect()
        except TypeError:
            pass

class CustomCardModel:
    view: CustomCardView

    def __init__(self, view):
        self.view = view
        self.card = None

    def set_card_object(self, card):
        self.card = card
        self.view.set_values([
            self.card.color.value,
            self.card.vocal,
            self.card.dance,
            self.card.visual,
            self.card.life,
            self.card.skill.duration,
            self.card.skill.interval
        ])

    def handle_cell_change(self, r_idx):
        v = self.view.widget.item(r_idx, 0).text()
        if r_idx == 0:
            self.card.color = Color(int(v))
        elif r_idx == 1:
            self.card.vo = float(v)
        elif r_idx == 2:
            self.card.da = float(v)
        elif r_idx == 3:
            self.card.vi = float(v)
        elif r_idx == 4:
            self.card.li = float(v)
        elif r_idx == 5:
            self.card.skill.duration = float(v)
        elif r_idx == 6:
            self.card.skill.interval = float(v)