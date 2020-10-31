from PyQt5.QtWidgets import QTableWidget, QAbstractItemView

from settings import IMAGE_PATH64
from src.exceptions import InvalidUnit
from src.gui.viewmodels.utils import NumericalTableWidgetItem, ImageWidget
from src.logic.grandlive import GrandLive
from src.logic.grandunit import GrandUnit
from src.logic.live import Live
from src.logic.unit import Unit


class SupportView:
    def __init__(self, main):
        self.widget = QTableWidget(main)
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
        support[:, [2, 3]] = support[:, [3, 2]]
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
        self.music = None
        self.card_ids = None

    def attach_custom_bonus_model(self, custom_bonus_model):
        self.custom_bonus_model = custom_bonus_model

    def attach_custom_settings_model(self, custom_settings_model):
        self.custom_settings_model = custom_settings_model

    def set_cards(self, cards):
        self.cards = cards
        try:
            custom_pots = self.custom_settings_model.get_custom_pots()
            if len(cards) == 15:
                unit = GrandUnit.from_list(self.cards, custom_pots)
                self.live = GrandLive()
                self.live.set_unit(unit)
            else:
                unit = Unit.from_list(self.cards, custom_pots)
                self.live = Live()
                self.live.set_unit(unit)
        except InvalidUnit:
            return False
        return True

    def set_music(self, score_id, difficulty):
        self.live.set_music(score_id=score_id, difficulty=difficulty, skip_load_notes=True)
        self.music = (score_id, difficulty)

    def generate_support(self):
        if self.live.unit is None:
            return
        if self.music is not None:
            self.live.set_music(score_id=self.music[0], difficulty=self.music[1])
        self.live.set_extra_bonus(*self.custom_bonus_model.get_bonus())
        self.live.get_support()
        self.view.display_support(self.live.support.copy())
        return self.live.get_appeals(), self.live.get_support(), self.live.get_life()
