from collections import OrderedDict

import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QTableWidgetItem

COLOR_PRESETS = OrderedDict({
    "All Colors": 1,
    "Cute": 2,
    "Cool": 3,
    "Passion": 4,
})
APPEAL_PRESETS = OrderedDict({
    "All Attributes": 1,
    "Vocal Groove": 2,
    "Dance Groove": 3,
    "Visual Groove": 4,
    "Vocal Only": 5,
    "Dance Only": 6,
    "Visual Only": 7,
    "Scale with Star Rank": 8,
    "Scale with Life": 9,
    "Scale with Potential": 10,
    "Event Idols": 11,
})


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
        self.apply_button = QtWidgets.QPushButton("Apply", self.main)
        self.reset_button = QtWidgets.QPushButton("Reset", self.main)
        self.custom_bonus_table = QtWidgets.QTableWidget(self.main)
        self._setup_values()

    def _setup_positions(self):
        self.layout.addWidget(self.custom_bonus_color_preset, 0, 0, 1, 2)
        self.layout.addWidget(self.custom_bonus_appeal_preset, 1, 0, 1, 2)
        self.layout.addWidget(self.custom_bonus_preset_value, 2, 0, 1, 2)
        self.layout.addWidget(self.apply_button, 3, 0, 1, 1)
        self.layout.addWidget(self.reset_button, 3, 1, 1, 1)
        self.layout.addWidget(self.custom_bonus_table, 0, 2, 4, 1)
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
        self.apply_button.pressed.connect(lambda: self.model.apply_bonus_template())
        self.reset_button.pressed.connect(lambda: self.model.clear_bonus_template())


class CustomBonusModel:
    view: CustomBonusView

    def __init__(self, view):
        self.view = view

    def get_bonus(self):
        appeal_idx = self.view.custom_bonus_appeal_preset.currentIndex()
        color_idx = self.view.custom_bonus_color_preset.currentIndex()
        results = np.zeros((3, 5))
        if appeal_idx in {
            APPEAL_PRESETS["Scale with Star Rank"],
            APPEAL_PRESETS["Scale with Life"],
            APPEAL_PRESETS["Scale with Potential"],
            APPEAL_PRESETS["Event Idols"],
        }:
            pass
            # TODO
        else:
            for r in range(3):
                for c in range(5):
                    results[r][c] = int(self.view.custom_bonus_table.item(r, c).text())
            results[:, [1, 2]] = results[:, [2, 1]]
        return results.transpose()

    def clear_bonus_template(self):
        for r in range(3):
            for c in range(5):
                item = QTableWidgetItem()
                item.setData(Qt.EditRole, 0)
                self.view.custom_bonus_table.setItem(r, c, item)

    def apply_bonus_template(self):
        appeal_idx = self.view.custom_bonus_appeal_preset.currentIndex()
        color_idx = self.view.custom_bonus_color_preset.currentIndex()
        if color_idx == 0 or appeal_idx == 0:
            return
        if appeal_idx == APPEAL_PRESETS["All Attributes"]:
            appeals = [1, 1, 1]
        elif appeal_idx == APPEAL_PRESETS["Vocal Groove"]:
            appeals = [1, 0, 0]
        elif appeal_idx == APPEAL_PRESETS["Dance Groove"]:
            appeals = [0, 1, 0]
        elif appeal_idx == APPEAL_PRESETS["Visual Groove"]:
            appeals = [0, 0, 1]
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

        value = self.view.custom_bonus_preset_value.text()
        if value == "":
            value = 0
        value = int(value)

        for r in range(3):
            for c in range(3):
                item = QTableWidgetItem()
                if appeals[c] == -99:
                    item.setData(Qt.EditRole, value * colors[r] * -9000 / value)
                else:
                    item.setData(Qt.EditRole, value * colors[r] * appeals[c])
                self.view.custom_bonus_table.setItem(r, c, item)
