from PyQt5.QtWidgets import QTableWidget, QAbstractItemView

from exceptions import InvalidUnit
from gui.viewmodels.utils import NumericalTableWidgetItem, ImageWidget
from logic.live import Live
from logic.unit import Unit
from settings import IMAGE_PATH64


class SupportView:
    def __init__(self, main):
        self.widget = QTableWidget(main)
        self.widget.setDragEnabled(True)
        self.widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.widget.setSortingEnabled(True)
        self.widget.verticalHeader().setVisible(False)
        self.widget.setRowCount(10)
        self.widget.setColumnCount(5)
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.horizontalHeader().setSectionResizeMode(1)  # Not allow change icon column size
        self.widget.setHorizontalHeaderLabels(["", "Vocal", "Dance", "Visual", "Total"])
        self.widget.verticalHeader().setDefaultSectionSize(72)

    def set_model(self, model):
        self.model = model

    def display_support(self, support):
        for r in range(len(support)):
            card_id = support[r][0]
            image = ImageWidget(str(IMAGE_PATH64 / "{:06d}.jpg".format(card_id)), self.widget)
            self.widget.setCellWidget(r, 0, image)
            for c in range(1, 5):
                self.widget.setItem(r, c, NumericalTableWidgetItem(support[r][c]))


class SupportModel:
    def __init__(self, view):
        self.view = view
        self.live = Live()
        self.card_ids = None

    def set_cards(self, cards_ids):
        self.card_ids = cards_ids
        try:
            unit = Unit.from_list(self.card_ids)
        except InvalidUnit:
            return
        self.live.set_unit(unit)

    def set_music(self, score_id, difficulty):
        self.live.set_music(score_id=score_id, difficulty=difficulty)

    def generate_support(self):
        if self.live.unit is None:
            return
        self.live.get_support()
        self.view.display_support(self.live.support)
