from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QAbstractItemView

from gui.viewmodels.utils import ValidatableNumericalTableWidgetItem
from static.color import Color

COLOR_KEY = "Color"
VOCAL_KEY = "Vocal"
DANCE_KEY = "Dance"
VISUAL_KEY = "Visual"
LIFE_KEY = "Life"
SKILL_DURATION_KEY = "Skill Duration"
SKILL_INTERVAL_KEY = "Skill Interval"
VOCAL_POTENTIAL_KEY = "Vocal Potential"
DANCE_POTENTIAL_KEY = "Dance Potential"
VISUAL_POTENTIAL_KEY = "Visual Potential"
LIFE_POTENTIAL_KEY = "Life Potential"
SKILL_POTENTIAL_KEY = "Skill Potential"
STAR_RANK_KEY = "Star Rank"

HEADERS = [COLOR_KEY,
           VOCAL_KEY, DANCE_KEY, VISUAL_KEY, LIFE_KEY,
           SKILL_DURATION_KEY, SKILL_INTERVAL_KEY,
           VOCAL_POTENTIAL_KEY, DANCE_POTENTIAL_KEY, VISUAL_POTENTIAL_KEY, LIFE_POTENTIAL_KEY, SKILL_POTENTIAL_KEY,
           STAR_RANK_KEY]


class CustomCardView:
    def __init__(self, main):
        self.widget = QtWidgets.QTableWidget(main)
        self.widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.widget.setSortingEnabled(False)
        self.widget.verticalHeader().setVisible(True)
        self.widget.horizontalHeader().setVisible(False)
        self.widget.setRowCount(len(HEADERS))
        self.widget.setColumnCount(1)
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.horizontalHeader().setSectionResizeMode(1)  # Not allow change icon column size
        self.widget.setVerticalHeaderLabels(HEADERS)
        self.widget.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def set_model(self, model):
        self.model = model

    def set_values(self, values):
        self.disconnect_cell_changed()
        if len(values) != len(HEADERS):
            return
        for _, header in enumerate(HEADERS):
            class_type = int
            if header == COLOR_KEY:
                validator = lambda x: 0 <= x <= 2
            elif header in {VOCAL_POTENTIAL_KEY, DANCE_POTENTIAL_KEY, VISUAL_POTENTIAL_KEY, LIFE_POTENTIAL_KEY,
                            SKILL_POTENTIAL_KEY}:
                validator = lambda x: 0 <= x <= 10
            elif header == STAR_RANK_KEY:
                validator = lambda x: 1 <= x <= 20
            else:
                validator = lambda x: True
            if header in {SKILL_DURATION_KEY, SKILL_INTERVAL_KEY}:
                class_type = float
            self.widget.setItem(_, 0, ValidatableNumericalTableWidgetItem(values[_], validator, class_type))
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
        if card is None:
            self.view.set_values([""] * len(HEADERS))
            self.view.widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        else:
            self.view.widget.setEditTriggers(QAbstractItemView.AllEditTriggers)
            self.view.set_values([
                self.card.color.value,
                self.card.base_vo,
                self.card.base_da,
                self.card.base_vi,
                self.card.base_li,
                self.card.skill.duration,
                self.card.skill.interval,
                self.card.vo_pots,
                self.card.da_pots,
                self.card.vi_pots,
                self.card.li_pots,
                self.card.sk_pots,
                self.card.star
            ])

    def handle_cell_change(self, r_idx):
        v = self.view.widget.item(r_idx, 0).text()
        if r_idx == 0:
            self.card.color = Color(int(v))
            self.card.skill.color = Color(int(v))
        elif r_idx == 1:
            self.card.base_vo = float(v)
        elif r_idx == 2:
            self.card.base_da = float(v)
        elif r_idx == 3:
            self.card.base_vi = float(v)
        elif r_idx == 4:
            self.card.base_li = float(v)
        elif r_idx == 5:
            self.card.skill.duration = float(v)
        elif r_idx == 6:
            self.card.skill.interval = float(v)
        elif r_idx == 7:
            self.card.vo_pots = int(v)
        elif r_idx == 8:
            self.card.da_pots = int(v)
        elif r_idx == 9:
            self.card.vi_pots = int(v)
        elif r_idx == 10:
            self.card.li_pots = int(v)
        elif r_idx == 11:
            self.card.sk_pots = int(v)
        elif r_idx == 12:
            self.card.star = int(v)
        self.card.refresh_values()
