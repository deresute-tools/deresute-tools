from PyQt5 import QtWidgets
from PyQt5.QtGui import QIntValidator

import customlogger as logger
from gui.events.chart_viewer_events import ToggleMirrorEvent
from gui.events.state_change_events import AutoFlagChangeEvent, PostYoinkEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.events.value_accessor_events import GetMirrorFlagEvent, GetPerfectPlayFlagEvent, GetCustomPotsEvent, \
    GetAppealsEvent, GetSupportEvent, GetDoublelifeFlagEvent, GetAutoplayFlagEvent, GetAutoplayOffsetEvent, \
    GetSkillBoundaryEvent, GetTheoreticalMaxFlagEvent


class CustomSettingsView:
    def __init__(self, main, main_model):
        self.layout = QtWidgets.QGridLayout()
        self.main = main
        self.main_model = main_model
        self._define_components()
        self._setup_positions()
        self._hook_events()

    def _define_components(self):
        self.custom_potential_checkbox = QtWidgets.QCheckBox("Custom Potentials", self.main)
        self.custom_appeal_checkbox = QtWidgets.QCheckBox("Total Appeal", self.main)
        self.custom_appeal_checkbox.setToolTip("This option will ignore support appeal.")
        self.custom_support_checkbox = QtWidgets.QCheckBox("Support Appeal", self.main)
        self.custom_perfect_play_checkbox = QtWidgets.QCheckBox("Perfect Simulation", self.main)
        self.theoretical_max_checkbox = QtWidgets.QCheckBox("Theoretical Max", self.main)
        self.theoretical_max_checkbox.setToolTip("Get the highest score theoretically possible. Will take some time.")
        self.skill_boundary = QtWidgets.QComboBox(self.main)
        self.skill_boundary.setToolTip("Change the way skill detection works.")
        self.mirror_checkbox = QtWidgets.QCheckBox("Mirror", self.main)
        self.doublelife_checkbox = QtWidgets.QCheckBox("2x Life Start", self.main)
        self.autoplay_mode_checkbox = QtWidgets.QCheckBox("Autoplay Mode", self.main)
        self.autoplay_offset_text = QtWidgets.QLineEdit(self.main)
        self.autoplay_offset_text.setPlaceholderText("Autoplay offset")
        self.autoplay_offset_text.setValidator(QIntValidator(0, 1E3, None))  # Only number allowed
        self.custom_appeal_text = QtWidgets.QLineEdit(self.main)
        self.custom_appeal_text.setValidator(QIntValidator(0, 1E6, None))  # Only number allowed
        self.custom_appeal_text.setPlaceholderText("Total appeals")
        self.custom_support_text = QtWidgets.QLineEdit(self.main)
        self.custom_support_text.setValidator(QIntValidator(0, 1E6, None))  # Only number allowed
        self.custom_support_text.setPlaceholderText("Support appeals")
        self.custom_vocal = QtWidgets.QComboBox(self.main)
        self.custom_dance = QtWidgets.QComboBox(self.main)
        self.custom_visual = QtWidgets.QComboBox(self.main)
        self.custom_life = QtWidgets.QComboBox(self.main)
        self.custom_skill = QtWidgets.QComboBox(self.main)
        self._setup_valid_potential_values()
        self._setup_skill_boundaries()

    def _setup_positions(self):
        self.layout.addWidget(self.custom_perfect_play_checkbox, 1, 0, 1, 2)
        self.layout.addWidget(self.mirror_checkbox, 1, 2, 1, 1)
        self.layout.addWidget(self.custom_potential_checkbox, 1, 3, 1, 2)
        self.layout.addWidget(self.theoretical_max_checkbox, 2, 0, 1, 2)
        self.layout.addWidget(self.skill_boundary, 2, 2, 1, 1)
        self.layout.addWidget(self.doublelife_checkbox, 2, 3, 1, 2)
        self.layout.addWidget(self.custom_support_text, 0, 5, 1, 1)
        self.layout.addWidget(self.custom_support_checkbox, 0, 6, 1, 1)
        self.layout.addWidget(self.custom_appeal_text, 1, 5, 1, 1)
        self.layout.addWidget(self.custom_appeal_checkbox, 1, 6, 1, 1)
        self.layout.addWidget(self.autoplay_offset_text, 2, 5, 1, 1)
        self.layout.addWidget(self.autoplay_mode_checkbox, 2, 6, 1, 1)
        self.layout.addWidget(self.custom_vocal, 0, 0, 1, 1)
        self.layout.addWidget(self.custom_dance, 0, 1, 1, 1)
        self.layout.addWidget(self.custom_visual, 0, 2, 1, 1)
        self.layout.addWidget(self.custom_life, 0, 3, 1, 1)
        self.layout.addWidget(self.custom_skill, 0, 4, 1, 1)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 1)
        self.layout.setColumnStretch(2, 1)
        self.layout.setColumnStretch(3, 1)
        self.layout.setColumnStretch(4, 1)
        self.layout.setColumnStretch(5, 2)
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

    def _setup_skill_boundaries(self):
        self.skill_boundary.addItem("Bound")
        self.skill_boundary.addItem("(  ]")
        self.skill_boundary.addItem("[  )")
        self.skill_boundary.addItem("[  ]")
        self.skill_boundary.addItem("(  )")

    def set_model(self, model):
        self.model = model
        self.model.hook_events()

    def _hook_events(self):
        self.autoplay_mode_checkbox.stateChanged.connect(
            lambda: eventbus.eventbus.post(AutoFlagChangeEvent(self.autoplay_mode_checkbox.isChecked())))


class CustomSettingsModel:
    view: CustomSettingsView

    def __init__(self, view):
        self.view = view
        self.card_ids = None
        eventbus.eventbus.register(self)

    @subscribe(GetCustomPotsEvent)
    def get_custom_pots(self, event=None):
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

    @subscribe(GetAppealsEvent)
    def get_appeals(self, event=None):
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

    @subscribe(GetSupportEvent)
    def get_support(self, event=None):
        if not self.view.custom_support_checkbox.isChecked():
            logger.debug("Not using custom support team")
            return None
        if self.view.custom_support_text.text() == "":
            return None
        return int(self.view.custom_support_text.text())

    @subscribe(PostYoinkEvent)
    def post_yoink_operations(self, event):
        support = event.support
        self.view.custom_support_checkbox.setChecked(True)
        self.view.custom_potential_checkbox.setChecked(False)
        self.set_support(support)

    @subscribe(GetPerfectPlayFlagEvent)
    def get_perfect_play(self, event=None):
        return self.view.custom_perfect_play_checkbox.isChecked()

    @subscribe(GetMirrorFlagEvent)
    def get_mirror(self, event=None):
        return self.view.mirror_checkbox.isChecked()

    @subscribe(GetDoublelifeFlagEvent)
    def get_doublelife(self, event=None):
        return self.view.doublelife_checkbox.isChecked()

    @subscribe(GetAutoplayFlagEvent)
    def get_autoplay(self, event=None):
        return self.view.autoplay_mode_checkbox.isChecked()

    @subscribe(GetAutoplayOffsetEvent)
    def get_autoplay_offset(self, event=None):
        if self.view.autoplay_offset_text.text() == "":
            return 0
        return int(self.view.autoplay_offset_text.text())

    @subscribe(GetTheoreticalMaxFlagEvent)
    def get_theoretical_max_flag(self, event=None):
        return self.view.theoretical_max_checkbox.isChecked()

    @subscribe(GetSkillBoundaryEvent)
    def get_skill_boundary(self, event=None):
        if self.view.skill_boundary.currentIndex() == 0 or self.view.skill_boundary.currentIndex() == 1:
            return False, True
        if self.view.skill_boundary.currentIndex() == 2:
            return True, False
        if self.view.skill_boundary.currentIndex() == 3:
            return True, True
        return False, False

    def hook_events(self):
        self.view.mirror_checkbox.toggled.connect(
            lambda: eventbus.eventbus.post(ToggleMirrorEvent(self.view.mirror_checkbox.isChecked())))
