import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QTableWidgetItem

from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.events.value_accessor_events import GetCustomBonusEvent, GetGrooveSongColor
from static.appeal_presets import APPEAL_PRESETS, COLOR_PRESETS
from static.color import Color


class CustomBonusView:
    def __init__(self, main, main_model):
        self.layout = QtWidgets.QGridLayout()
        self.main = main
        self.main_model = main_model
        self._define_components()
        self._setup_positions()

    def _define_components(self):
        self.custom_bonus_color_preset = QtWidgets.QComboBox(self.main)
        self.custom_bonus_appeal_preset = QtWidgets.QComboBox(self.main)
        self.custom_bonus_preset_value = QtWidgets.QLineEdit(self.main)
        self.custom_bonus_table = QtWidgets.QTableWidget(self.main)
        self._setup_values()

    def _setup_positions(self):
        self.layout.addWidget(self.custom_bonus_color_preset, 0, 0, 1, 1)
        self.layout.addWidget(self.custom_bonus_appeal_preset, 1, 0, 1, 1)
        self.layout.addWidget(self.custom_bonus_preset_value, 2, 0, 1, 1)
        self.layout.addWidget(self.custom_bonus_table, 0, 1, 3, 3)
        self.custom_bonus_table.horizontalHeader().setSectionResizeMode(1)  # Auto fit
        self.custom_bonus_table.verticalHeader().setSectionResizeMode(1)  # Auto fit
        self.custom_bonus_table.setMinimumHeight(100)

    def _setup_values(self):
        self.custom_bonus_color_preset.addItem("Color Presets")
        for color_preset in COLOR_PRESETS.keys():
            self.custom_bonus_color_preset.addItem(color_preset)
        self.custom_bonus_appeal_preset.addItem("Appeal Presets")
        for appeal_preset in APPEAL_PRESETS.keys():
            self.custom_bonus_appeal_preset.addItem(appeal_preset)
        self.custom_bonus_appeal_preset.setMaxVisibleItems(12)
        self.custom_bonus_preset_value.setValidator(QIntValidator(-9000, 9000, None))  # Only number allowed
        self.custom_bonus_preset_value.setText("0")
        self.custom_bonus_preset_value.textEdited.connect(lambda _: self.model.apply_bonus_template())
        self.custom_bonus_color_preset.currentIndexChanged.connect(lambda _: self.model.apply_bonus_template())
        self.custom_bonus_appeal_preset.currentIndexChanged.connect(lambda _: self.model.apply_bonus_template())
        self.custom_bonus_table.setRowCount(3)
        self.custom_bonus_table.setColumnCount(5)
        self.custom_bonus_table.setHorizontalHeaderLabels(["Vocal", "Dance", "Visual", "Life", "Skill"])
        self.custom_bonus_table.setVerticalHeaderLabels(["Cute", "Cool", "Passion"])
        for r in range(3):
            for c in range(5):
                item = QTableWidgetItem()
                item.setData(Qt.EditRole, 0)
                self.custom_bonus_table.setItem(r, c, item)

    def set_model(self, model):
        self.model = model


class CustomBonusModel:
    view: CustomBonusView

    def __init__(self, view):
        self.view = view
        eventbus.eventbus.register(self)

    @subscribe(GetGrooveSongColor)
    def get_groove_color(self, event=None):
        appeal_idx = self.view.custom_bonus_appeal_preset.currentIndex()
        is_groove = appeal_idx == APPEAL_PRESETS["Vocal Groove"] or appeal_idx == APPEAL_PRESETS[
            "Dance Groove"] or appeal_idx == APPEAL_PRESETS["Visual Groove"]

        if not is_groove:
            return None
        color_idx = self.view.custom_bonus_color_preset.currentIndex()
        if color_idx == COLOR_PRESETS["Cute"]:
            return Color.CUTE
        if color_idx == COLOR_PRESETS["Cool"]:
            return Color.COOL
        if color_idx == COLOR_PRESETS["Passion"]:
            return Color.PASSION
        return Color.ALL

    @subscribe(GetCustomBonusEvent)
    def get_bonus(self, event=None):
        appeal_idx = self.view.custom_bonus_appeal_preset.currentIndex()
        results = np.zeros((3, 5))
        if appeal_idx in {
            APPEAL_PRESETS["Scale with Star Rank"],
            APPEAL_PRESETS["Scale with Life"],
            APPEAL_PRESETS["Scale with Potential"],
            APPEAL_PRESETS["Event Idols"],
        }:
            if self.view.custom_bonus_preset_value.text() == "":
                value = 0
            else:
                value = int(self.view.custom_bonus_preset_value.text())
            return None, appeal_idx, value
        else:
            for r in range(3):
                for c in range(5):
                    results[r][c] = int(self.view.custom_bonus_table.item(r, c).text())
            results[:, [1, 2]] = results[:, [2, 1]]
        return results.transpose(), None, None

    def clear_bonus_template(self):
        for r in range(3):
            for c in range(5):
                item = QTableWidgetItem()
                item.setData(Qt.EditRole, 0)
                self.view.custom_bonus_table.setItem(r, c, item)

    def apply_groove_bonus(self, appeal_idx, value):
        if appeal_idx == APPEAL_PRESETS["Vocal Groove"]:
            match_c = 0
        elif appeal_idx == APPEAL_PRESETS["Dance Groove"]:
            match_c = 1
        elif appeal_idx == APPEAL_PRESETS["Visual Groove"]:
            match_c = 2
        for r in range(3):
            for c in range(3):
                if c == match_c:
                    base_value = value
                else:
                    base_value = 0
                item = QTableWidgetItem()
                item.setData(Qt.EditRole, base_value)
                self.view.custom_bonus_table.setItem(r, c, item)

    def apply_bonus_template(self):
        text = self.view.custom_bonus_preset_value.text()
        if text == "" or text == "-":
            value = 0
        else:
            value = int(text)
        appeal_idx = self.view.custom_bonus_appeal_preset.currentIndex()
        color_idx = self.view.custom_bonus_color_preset.currentIndex()
        if color_idx == 0 or appeal_idx == 0:
            return
        if appeal_idx == APPEAL_PRESETS["All Attributes"]:
            appeals = [1, 1, 1]
        elif appeal_idx == APPEAL_PRESETS["Vocal Groove"] \
                or appeal_idx == APPEAL_PRESETS["Dance Groove"] \
                or appeal_idx == APPEAL_PRESETS["Visual Groove"]:
            self.clear_bonus_template()
            self.apply_groove_bonus(appeal_idx, value)
            return
        elif appeal_idx == APPEAL_PRESETS["Vocal Only"]:
            appeals = [1, -99, -99]
        elif appeal_idx == APPEAL_PRESETS["Dance Only"]:
            appeals = [-99, 1, -99]
        elif appeal_idx == APPEAL_PRESETS["Visual Only"]:
            appeals = [-99, -99, 1]
        else:
            self.clear_bonus_template()
            return
        if color_idx == COLOR_PRESETS["All Colors"]:
            colors = [1, 1, 1]
        elif color_idx == COLOR_PRESETS["Cute"]:
            colors = [1, 0, 0]
        elif color_idx == COLOR_PRESETS["Cool"]:
            colors = [0, 1, 0]
        elif color_idx == COLOR_PRESETS["Passion"]:
            colors = [0, 0, 1]
        else:
            raise ValueError("Invalid Color Preset. This error shouldn't throw.")

        for r in range(3):
            for c in range(3):
                item = QTableWidgetItem()
                if appeals[c] == -99:
                    if value == 0:
                        continue
                    item.setData(Qt.EditRole, value * colors[r] * -9000 / value)
                else:
                    item.setData(Qt.EditRole, value * colors[r] * appeals[c])
                self.view.custom_bonus_table.setItem(r, c, item)
