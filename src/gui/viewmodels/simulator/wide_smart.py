import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIntValidator

from src.exceptions import InvalidUnit
from src.gui.viewmodels.simulator.calculator import CalculatorView, CalculatorModel
from src.gui.viewmodels.simulator.custom_bonus import CustomBonusView, CustomBonusModel
from src.gui.viewmodels.simulator.custom_settings import CustomSettingsView, CustomSettingsModel
from src.gui.viewmodels.simulator.support import SupportView, SupportModel
from src.logic.live import Live
from src.logic.unit import Unit
from src.simulator import Simulator
from src import customlogger as logger


class MainView:
    def __init__(self):
        self.widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QHBoxLayout(self.widget)

    def setup(self):
        self.calculator_and_custom_setting_layout = QtWidgets.QVBoxLayout()
        self._set_up_calculator()
        self.bottom_row_layout = QtWidgets.QHBoxLayout()
        self._set_up_big_buttons()
        self._setup_custom_settings()
        self.calculator_and_custom_setting_layout.addLayout(self.bottom_row_layout)
        self.bottom_row_layout.setStretch(0, 1)
        self.bottom_row_layout.setStretch(1, 5)
        self.calculator_and_custom_setting_layout.setStretch(0, 1)

        self.custom_appeal_and_support_layout = QtWidgets.QVBoxLayout()
        self._setup_custom_bonus()
        self._setup_support()

        self.calculator_table_view.set_support_model(self.support_model)
        self.calculator_table_view.attach_custom_settings_model(self.custom_settings_model)

        self.main_layout.addLayout(self.calculator_and_custom_setting_layout)
        self.main_layout.addLayout(self.custom_appeal_and_support_layout)
        self.main_layout.setStretch(0, 1)

    def _setup_custom_bonus(self):
        self.custom_bonus_view = CustomBonusView(self.widget, self.model)
        self.custom_bonus_model = CustomBonusModel(self.custom_bonus_view)
        self.custom_bonus_view.set_model(self.custom_bonus_model)
        self.custom_appeal_and_support_layout.addLayout(self.custom_bonus_view.layout)

    def _setup_support(self):
        self.support_view = SupportView(self.widget)
        self.support_model = SupportModel(self.support_view)
        self.support_model.attach_custom_bonus_model(self.custom_bonus_model)
        self.support_model.attach_custom_settings_model(self.custom_settings_model)
        self.support_view.set_model(self.support_model)
        self.custom_appeal_and_support_layout.addWidget(self.support_view.widget)

    def _set_up_calculator(self):
        self.calculator_table_view = CalculatorView(self.widget, self)
        self.calculator_table_model = CalculatorModel(self.calculator_table_view)
        self.calculator_table_view.set_model(self.calculator_table_view)
        self.calculator_and_custom_setting_layout.addWidget(self.calculator_table_view.widget)

    def _set_up_big_buttons(self):
        self.button_layout = QtWidgets.QGridLayout()
        self.big_button = QtWidgets.QPushButton("Run", self.widget)
        self.add_button = QtWidgets.QPushButton("Add Empty Unit", self.widget)
        self.clear_button = QtWidgets.QPushButton("Clear All Units", self.widget)
        self.times_text = QtWidgets.QLineEdit(self.widget)
        self.times_text.setValidator(QIntValidator(0, 100, None))  # Only number allowed
        self.times_text.setText("10")
        self.times_label = QtWidgets.QLabel("times", self.widget)

        font = self.big_button.font()
        font.setPointSize(16)
        self.big_button.setFont(font)

        self.add_button.pressed.connect(lambda: self.calculator_table_view.add_empty_unit())
        self.clear_button.pressed.connect(lambda: self.calculator_table_view.clear_units())
        self.big_button.pressed.connect(lambda: self.simulate())

        self.button_layout.addWidget(self.big_button, 0, 0, 1, 2)
        self.button_layout.addWidget(self.times_text, 1, 0, 1, 1)
        self.button_layout.addWidget(self.times_label, 1, 1, 1, 1)
        self.button_layout.addWidget(self.add_button, 0, 2, 1, 1)
        self.button_layout.addWidget(self.clear_button, 1, 2, 1, 1)
        self.bottom_row_layout.addLayout(self.button_layout)

    def _setup_custom_settings(self):
        self.custom_settings_view = CustomSettingsView(self.widget, self.model)
        self.custom_settings_model = CustomSettingsModel(self.custom_settings_view)
        self.custom_settings_view.set_model(self.custom_settings_model)
        self.bottom_row_layout.addLayout(self.custom_settings_view.layout)

    def set_model(self, model):
        self.model = model

    def attach_song_view(self, song_view):
        self.song_view = song_view

    def get_song(self):
        row_idx = self.song_view.widget.selectionModel().currentIndex().row()
        if row_idx == -1:
            return None, None
        score_id = int(self.song_view.widget.item(row_idx, 11).text())
        diff_id = int(self.song_view.widget.item(row_idx, 12).text())
        return score_id, diff_id

    def get_times(self):
        if self.times_text.text() == "" or self.times_text.text() == "0":
            return 10
        else:
            return int(self.times_text.text())

    def simulate(self, row=None):
        score_id, diff_id = self.get_song()
        if diff_id is None:
            logger.info("No chart loaded")
            return
        times = self.get_times()
        all_cards = self.calculator_table_model.get_all_cards()
        custom_pots = self.custom_settings_model.get_custom_pots()
        appeals = self.custom_settings_model.get_appeals()
        support = self.custom_settings_model.get_support()
        extra_bonus = self.custom_bonus_model.get_bonus()
        self.model.simulate_internal(
            score_id=score_id, diff_id=diff_id, times=times, all_cards=all_cards, custom_pots=custom_pots,
            appeals=appeals, support=support, extra_bonus=extra_bonus,
            row=row
        )

    def display_results(self, results, row=None):
        self.calculator_table_view.display_results(results, row=row)


class MainModel:
    view: MainView

    def __init__(self, view):
        self.view = view

    def simulate_internal(self, score_id, diff_id, times, all_cards, custom_pots, appeals, support, extra_bonus,
                          row=None):
        results = list()

        live = Live()
        live.set_music(score_id=score_id, difficulty=diff_id)
        if row is not None:
            all_cards = [all_cards[row]]
        for cards in all_cards:
            # Load cards
            if cards[5] is None:
                cards = cards[:5]
            try:
                unit = Unit.from_list(cards, custom_pots)
            except InvalidUnit:
                logger.info("Invalid unit: {}".format(cards))
                results.append(None)
                continue

            live.set_unit(unit)
            sim = Simulator(live)
            results.append(sim.simulate(times=times, appeals=appeals, extra_bonus=extra_bonus, support=support,
                                        perfect_play=False))
        self.process_results(results, row)

    def process_results(self, results, row=None):
        # ["Perfect", "Mean", "Max", "Min", "Skill Off", "1%", "5%", "25%", "50%", "75%"])
        # results: appeals, perfect_score, skill_off, base, deltas
        res = list()
        for result in results:
            temp = list()
            appeals, perfect_score, skill_off, base, deltas = result
            temp.append(appeals)
            temp.append(perfect_score)
            temp.append(base)
            temp.append(base + deltas.max())
            temp.append(base + deltas.min())
            temp.append(skill_off)
            temp.append(base + np.percentile(deltas, 95))
            temp.append(base + np.percentile(deltas, 75))
            temp.append(base + np.percentile(deltas, 50))
            temp.append(base + np.percentile(deltas, 25))
            res.append(map(int, temp))
        self.view.display_results(res, row)
