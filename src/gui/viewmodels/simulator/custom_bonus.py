import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QTableWidgetItem


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
        self.custom_bonus_color_preset.addItem("All Colors")
        self.custom_bonus_color_preset.addItem("Cute")
        self.custom_bonus_color_preset.addItem("Cool")
        self.custom_bonus_color_preset.addItem("Passion")
        self.custom_bonus_appeal_preset.addItem("Appeal Presets")
        self.custom_bonus_appeal_preset.addItem("All Attributes")
        self.custom_bonus_appeal_preset.addItem("Vocal Groove")
        self.custom_bonus_appeal_preset.addItem("Dance Groove")
        self.custom_bonus_appeal_preset.addItem("Visual Groove")
        self.custom_bonus_appeal_preset.addItem("Vocal Only")
        self.custom_bonus_appeal_preset.addItem("Dance Only")
        self.custom_bonus_appeal_preset.addItem("Visual Only")
        self.custom_bonus_appeal_preset.addItem("Scale with Star Rank")
        self.custom_bonus_appeal_preset.addItem("Scale with Life")
        self.custom_bonus_appeal_preset.addItem("Scale with Potential")
        self.custom_bonus_appeal_preset.addItem("Event Idols")
        self.custom_bonus_appeal_preset.setMaxVisibleItems(12)
        self.custom_bonus_preset_value.setValidator(QIntValidator(0, 1000, None))  # Only number allowed
        self.custom_bonus_table.setRowCount(3)
        self.custom_bonus_table.setColumnCount(3)
        self.custom_bonus_table.setHorizontalHeaderLabels(["Vocal", "Dance", "Visual"])
        self.custom_bonus_table.setVerticalHeaderLabels(["Cute", "Cool", "Passion"])
        for r in range(3):
            for c in range(3):
                item = QTableWidgetItem()
                item.setData(Qt.EditRole, 0)
                self.custom_bonus_table.setItem(r, c, item)

    def set_model(self, model):
        self.model = model


class CustomBonusModel:
    view: CustomBonusView

    def __init__(self, view):
        self.view = view

    def get_bonus(self):
        results = np.zeros((3, 3))
        for r in range(3):
            for c in range(3):
                results[r][c] = int(self.view.custom_bonus_table.item(r, c).text())
        results[:, [1, 2]] = results[:, [2, 1]]
        return results.transpose()
