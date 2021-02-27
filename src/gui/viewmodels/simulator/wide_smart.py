import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QSizePolicy, QTabWidget

import customlogger as logger
from exceptions import InvalidUnit
from gui.viewmodels.simulator.calculator import CalculatorModel, CalculatorView
from gui.viewmodels.simulator.custom_bonus import CustomBonusView, CustomBonusModel
from gui.viewmodels.simulator.custom_card import CustomCardView, CustomCardModel
from gui.viewmodels.simulator.custom_settings import CustomSettingsView, CustomSettingsModel
from gui.viewmodels.simulator.grandcalculator import GrandCalculatorView
from gui.viewmodels.simulator.support import SupportView, SupportModel
from logic.grandlive import GrandLive
from logic.grandunit import GrandUnit
from logic.live import Live
from logic.unit import Unit
from simulator import Simulator


class MainView:
    def __init__(self):
        self.widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QHBoxLayout(self.widget)

    def setup(self):
        self.calculator_and_custom_setting_layout = QtWidgets.QVBoxLayout()
        self.bottom_row_layout = QtWidgets.QHBoxLayout()
        self._set_up_big_buttons()
        self._setup_custom_settings()
        self.bottom_row_layout.setStretch(0, 1)
        self.bottom_row_layout.setStretch(1, 5)
        self.calculator_and_custom_setting_layout.setStretch(0, 1)
        self.custom_appeal_and_support_layout = QtWidgets.QVBoxLayout()
        self._setup_custom_bonus()
        self._setup_custom_card_and_support()
        self._set_up_calculator()
        self.calculator_and_custom_setting_layout.addLayout(self.bottom_row_layout)
        self.main_layout.addLayout(self.calculator_and_custom_setting_layout)
        self.main_layout.addLayout(self.custom_appeal_and_support_layout)
        self.main_layout.setStretch(0, 1)

    def _setup_custom_bonus(self):
        self.custom_bonus_view = CustomBonusView(self.widget, self.model)
        self.custom_bonus_model = CustomBonusModel(self.custom_bonus_view)
        self.custom_bonus_view.set_model(self.custom_bonus_model)
        self.custom_appeal_and_support_layout.addLayout(self.custom_bonus_view.layout)

    def _setup_custom_card_and_support(self):
        self.custom_card_and_support_widget = QTabWidget(self.widget)
        self._setup_support()
        self._setup_custom_card()
        self.custom_card_and_support_widget.addTab(self.support_view.widget, "Support Team")
        self.custom_card_and_support_widget.addTab(self.custom_card_view.widget, "Custom Card")
        self.custom_appeal_and_support_layout.addWidget(self.custom_card_and_support_widget)

    def _setup_custom_card(self):
        self.custom_card_view = CustomCardView(self.widget)
        self.custom_card_model = CustomCardModel(self.custom_card_view)
        self.custom_card_view.set_model(self.custom_card_model)

    def _setup_support(self):
        self.support_view = SupportView(self.widget)
        self.support_model = SupportModel(self.support_view)
        self.support_model.attach_custom_bonus_model(self.custom_bonus_model)
        self.support_model.attach_custom_settings_model(self.custom_settings_model)
        self.support_view.set_model(self.support_model)

    def _set_up_calculator(self):
        self.calculator_tabs = QtWidgets.QTabWidget(self.widget)
        view_wide = CalculatorView(self.widget, self)
        view_grand = GrandCalculatorView(self.widget, self)
        self.views = [view_wide, view_grand]
        self.calculator_tabs.addTab(view_wide.widget, "WIDE")
        self.calculator_tabs.addTab(view_grand.widget, "GRAND")
        self.calculator_and_custom_setting_layout.addWidget(self.calculator_tabs)
        self.calculator_tabs.setCurrentIndex(0)
        self._switch_tab(0)
        self.calculator_tabs.currentChanged.connect(lambda idx: self._switch_tab(idx))

    def _switch_tab(self, idx):
        self.calculator_table_model = CalculatorModel(self.views[idx])
        self.views[idx].set_model(self.calculator_table_model)
        try:
            self.add_button.pressed.disconnect()
            self.clear_button.pressed.disconnect()
            self.permute_button.pressed.disconnect()
        except TypeError:
            pass
        self.add_button.pressed.connect(lambda: self.views[idx].add_empty_unit())
        self.clear_button.pressed.connect(lambda: self.views[idx].clear_units())
        if idx == 1:
            self.permute_button.pressed.connect(lambda: self.views[idx].permute_units())
        self.calculator_table_view = self.views[idx]
        self.views[idx].set_support_model(self.support_model)
        self.views[idx].attach_custom_settings_model(self.custom_settings_model)

    def get_table_view(self):
        return self.calculator_table_view

    def get_table_model(self):
        return self.calculator_table_model

    def _set_up_big_buttons(self):
        self.button_layout = QtWidgets.QGridLayout()
        self.big_button = QtWidgets.QPushButton("Run", self.widget)
        self.add_button = QtWidgets.QPushButton("Add Empty Unit", self.widget)
        self.clear_button = QtWidgets.QPushButton("Clear All Units", self.widget)
        self.permute_button = QtWidgets.QPushButton("Permute Units", self.widget)
        self.times_text = QtWidgets.QLineEdit(self.widget)
        self.times_text.setValidator(QIntValidator(0, 100, None))  # Only number allowed
        self.times_text.setText("10")
        self.times_label = QtWidgets.QLabel("times", self.widget)

        font = self.big_button.font()
        font.setPointSize(16)
        self.big_button.setFont(font)
        self.big_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        self.big_button.pressed.connect(lambda: self.simulate())

        self.button_layout.addWidget(self.big_button, 0, 0, 2, 2)
        self.button_layout.addWidget(self.times_text, 2, 0, 1, 1)
        self.button_layout.addWidget(self.times_label, 2, 1, 1, 1)
        self.button_layout.addWidget(self.add_button, 0, 2, 1, 1)
        self.button_layout.addWidget(self.clear_button, 1, 2, 1, 1)
        self.button_layout.addWidget(self.permute_button, 2, 2, 1, 1)
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
        score_id = int(self.song_view.widget.item(row_idx, 1).text())
        diff_id = int(self.song_view.widget.item(row_idx, 2).text())
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
        all_cards = self.get_table_model().get_all_cards()
        perfect_play = self.custom_settings_model.get_perfect_play()
        custom_pots = self.custom_settings_model.get_custom_pots()
        appeals = self.custom_settings_model.get_appeals()
        support = self.custom_settings_model.get_support()
        mirror = self.custom_settings_model.get_mirror()
        doublelife = self.custom_settings_model.get_doublelife()
        autoplay = self.custom_settings_model.get_autoplay()
        autoplay_offset = self.custom_settings_model.get_autoplay_offset()
        extra_bonus, special_option, special_value = self.custom_bonus_model.get_bonus()
        self.model.simulate_internal(
            perfect_play=perfect_play,
            score_id=score_id, diff_id=diff_id, times=times, all_cards=all_cards, custom_pots=custom_pots,
            appeals=appeals, support=support, extra_bonus=extra_bonus,
            special_option=special_option, special_value=special_value,
            mirror=mirror, autoplay=autoplay, autoplay_offset=autoplay_offset,
            doublelife=doublelife,
            row=row
        )

    def display_results(self, results, row=None, autoplay=False):
        self.get_table_view().widget.setSortingEnabled(False)
        self.get_table_view().display_results(results, row=row, autoplay=autoplay)
        self.get_table_view().widget.setSortingEnabled(True)


class MainModel:
    view: MainView

    def __init__(self, view):
        self.view = view

    def simulate_internal(self, perfect_play, score_id, diff_id, times, all_cards, custom_pots, appeals, support,
                          extra_bonus, special_option, special_value,
                          mirror, autoplay, autoplay_offset,
                          doublelife,
                          row=None):
        results = list()
        if len(all_cards) == 0:
            logger.info("Nothing to simulate")
            return
        if row is not None:
            all_cards = [all_cards[row]]
        for cards in all_cards:
            if len(cards) == 15:
                live = GrandLive()
            else:
                live = Live()
            live.set_music(score_id=score_id, difficulty=diff_id)
            # Load cards
            try:
                if len(cards) == 15:
                    unit = GrandUnit.from_list(cards, custom_pots)
                else:
                    if cards[5] is None:
                        cards = cards[:5]
                    unit = Unit.from_list(cards, custom_pots)
            except InvalidUnit:
                logger.info("Invalid unit: {}".format(cards))
                results.append(None)
                continue

            live.set_unit(unit)
            if autoplay:
                sim = Simulator(live, special_offset=0.075)
                results.append(sim.simulate_auto(appeals=appeals, extra_bonus=extra_bonus, support=support,
                                                 special_option=special_option, special_value=special_value,
                                                 time_offset=autoplay_offset, mirror=mirror,
                                                 doublelife=doublelife))
            else:
                sim = Simulator(live)
                results.append(sim.simulate(perfect_play=perfect_play,
                                            times=times, appeals=appeals, extra_bonus=extra_bonus, support=support,
                                            special_option=special_option, special_value=special_value,
                                            doublelife=doublelife))
        self.process_results(results, row, autoplay)

    def process_results(self, results, row=None, auto=False):
        if auto:
            self._process_auto_results(results, row)
        else:
            self._process_normal_results(results, row)

    def _process_normal_results(self, results, row=None):
        # ["Perfect", "Mean", "Max", "Min", "Skill Off", "1%", "5%", "25%", "50%", "75%"])
        # results: appeals, perfect_score, skill_off, base, deltas
        res = list()
        for result in results:
            temp = list()
            if result is None:
                temp.append(None)
                continue
            appeals, perfect_score, skill_off, base, deltas, life = result
            temp.append(appeals)
            temp.append(life)
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
        self.view.display_results(res, row, autoplay=False)

    def _process_auto_results(self, results, row=None):
        # ["Auto Score", "Perfects", "Misses", "Max Combo", "Lowest Life", "Lowest Life Time", "All Skills 100%?"]
        # results: score, perfects, misses. max_combo, lowest_life, lowest_life_time, self.all_100
        res = list()
        for result in results:
            temp = list()
            if result is None:
                temp.append(None)
                continue
            appeals, life, score, perfects, misses, max_combo, lowest_life, lowest_life_time, all_100 = result
            temp.append(int(appeals))
            temp.append(int(life))
            temp.append(int(score))
            temp.append(int(perfects))
            temp.append(int(misses))
            temp.append(int(max_combo))
            temp.append(int(lowest_life))
            temp.append(float(lowest_life_time))
            temp.append("Yes" if all_100 else "No")
            res.append(temp)
        self.view.display_results(res, row, autoplay=True)
