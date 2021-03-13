from PyQt5 import QtWidgets
from PyQt5.QtGui import QIntValidator

import customlogger as logger


class CustomSettingsView:
    def __init__(self, main, main_model):
        self.layout = QtWidgets.QGridLayout()
        self.main = main
        self.main_model = main_model
        self._define_components()
        self._setup_positions()

    def _define_components(self):
        self.custom_potential_checkbox = QtWidgets.QCheckBox("Custom Potentials", self.main)
        self.custom_appeal_checkbox = QtWidgets.QCheckBox("Total Appeal", self.main)
        self.custom_appeal_checkbox.setToolTip("This option will ignore support appeal.")
        self.custom_support_checkbox = QtWidgets.QCheckBox("Support Appeal", self.main)
        self.custom_perfect_play_checkbox = QtWidgets.QCheckBox("Perfect Simulation", self.main)
        self.autoplay_mode_checkbox = QtWidgets.QCheckBox("Autoplay Mode", self.main)
        self.mirror_checkbox = QtWidgets.QCheckBox("Mirror", self.main)
        self.doublelife_checkbox = QtWidgets.QCheckBox("2x Life Start", self.main)
        self.autoplay_offset_text = QtWidgets.QLineEdit(self.main)
        self.autoplay_offset_text.setPlaceholderText("Set autoplay offset in milliseconds")
        self.autoplay_offset_text.setValidator(QIntValidator(0, 1E3, None))  # Only number allowed
        self.custom_appeal_text = QtWidgets.QLineEdit(self.main)
        self.custom_appeal_text.setValidator(QIntValidator(0, 1E6, None))  # Only number allowed
        self.custom_support_text = QtWidgets.QLineEdit(self.main)
        self.custom_support_text.setValidator(QIntValidator(0, 1E6, None))  # Only number allowed
        self.custom_vocal = QtWidgets.QComboBox(self.main)
        self.custom_dance = QtWidgets.QComboBox(self.main)
        self.custom_visual = QtWidgets.QComboBox(self.main)
        self.custom_life = QtWidgets.QComboBox(self.main)
        self.custom_skill = QtWidgets.QComboBox(self.main)
        self._setup_valid_potential_values()

    def _setup_positions(self):
        self.layout.addWidget(self.custom_perfect_play_checkbox, 2, 0, 1, 3)
        self.layout.addWidget(self.custom_potential_checkbox, 2, 3, 1, 2)
        self.layout.addWidget(self.autoplay_mode_checkbox, 3, 0, 1, 2)
        self.layout.addWidget(self.mirror_checkbox, 3, 2, 1, 1)
        self.layout.addWidget(self.doublelife_checkbox, 3, 3, 1, 2)
        self.layout.addWidget(self.autoplay_offset_text, 3, 5, 1, 2)
        self.layout.addWidget(self.custom_appeal_checkbox, 2, 5, 1, 1)
        self.layout.addWidget(self.custom_support_checkbox, 2, 6, 1, 1)
        self.layout.addWidget(self.custom_appeal_text, 1, 5, 1, 1)
        self.layout.addWidget(self.custom_support_text, 1, 6, 1, 1)
        self.layout.addWidget(self.custom_vocal, 1, 0, 1, 1)
        self.layout.addWidget(self.custom_dance, 1, 1, 1, 1)
        self.layout.addWidget(self.custom_visual, 1, 2, 1, 1)
        self.layout.addWidget(self.custom_life, 1, 3, 1, 1)
        self.layout.addWidget(self.custom_skill, 1, 4, 1, 1)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 1)
        self.layout.setColumnStretch(2, 1)
        self.layout.setColumnStretch(3, 1)
        self.layout.setColumnStretch(4, 1)
        self.layout.setColumnStretch(5, 1)
        self.layout.setColumnStretch(6, 1)

    def _setup_valid_potential_values(self):
        for key, combobox in zip(
                ["Vocal", "Dance", "Visual", "Life", "Skill"],
                [self.custom_vocal, self.custom_dance, self.custom_visual, self.custom_life, self.custom_skill]
        ):
            combobox.addItem(key)
            for _ in range(1, 11):
                combobox.addItem(str(_))
            combobox.setMaxVisibleItems(11)

    def set_model(self, model):
        self.model = model


class CustomSettingsModel:
    view: CustomSettingsView

    def __init__(self, view):
        self.view = view
        self.card_ids = None

    def get_custom_pots(self):
        if not self.view.custom_potential_checkbox.isChecked():
            logger.debug("Not using custom potentials")
            return None
        results = list()
        results.append(self.view.custom_vocal.currentIndex())
        results.append(self.view.custom_visual.currentIndex())
        results.append(self.view.custom_dance.currentIndex())
        results.append(self.view.custom_life.currentIndex())
        results.append(self.view.custom_skill.currentIndex())
        return results

    def get_appeals(self):
        if not self.view.custom_appeal_checkbox.isChecked():
            logger.debug("Not using custom appeals")
            return None
        if self.view.custom_appeal_text.text() == "":
            return None
        return int(self.view.custom_appeal_text.text())

    def set_support(self, appeal):
        try:
            assert isinstance(appeal, int) and appeal > 0
            self.view.custom_support_text.setText(str(appeal))
        except AssertionError:
            pass

    def get_support(self):
        if not self.view.custom_support_checkbox.isChecked():
            logger.debug("Not using custom support team")
            return None
        if self.view.custom_support_text.text() == "":
            return None
        return int(self.view.custom_support_text.text())

    def enable_custom_support(self):
        self.view.custom_support_checkbox.setChecked(True)

    def get_perfect_play(self):
        return self.view.custom_perfect_play_checkbox.isChecked()

    def get_mirror(self):
        return self.view.mirror_checkbox.isChecked()

    def get_doublelife(self):
        return self.view.doublelife_checkbox.isChecked()

    def get_autoplay(self):
        return self.view.autoplay_mode_checkbox.isChecked()

    def get_autoplay_offset(self):
        if self.view.autoplay_offset_text.text() == "":
            return 0
        return int(self.view.autoplay_offset_text.text())
