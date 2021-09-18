from PyQt5 import QtWidgets
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QSizePolicy

import customlogger as logger
from gui.events.chart_viewer_events import ToggleMirrorEvent
from gui.events.state_change_events import AutoFlagChangeEvent, PostYoinkEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.events.value_accessor_events import GetMirrorFlagEvent, GetPerfectPlayFlagEvent, GetCustomPotsEvent, \
    GetAppealsEvent, GetSupportEvent, GetDoublelifeFlagEvent, GetAutoplayFlagEvent, GetAutoplayOffsetEvent, \
    GetSkillBoundaryEvent, GetTheoreticalMaxFlagEvent, GetEncoreAMRFlagEvent, GetEncoreMagicUnitFlagEvent, \
    GetEncoreMagicMaxAggEvent, GetAllowGreatEvent


class CustomSettingsView:
    def __init__(self, main, main_model):
        self.main = main
        self.main_model = main_model
        self._setup_tabs()
        self._define_components_1()
        self._setup_positions_1()
        self._define_components_2()
        self._setup_positions_2()
        self._hook_events()

    def _setup_tabs(self):
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setMaximumHeight(100)
        self.tab_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.tab_widget.setTabPosition(QtWidgets.QTabWidget.East)
        tab1 = QtWidgets.QFrame(self.main)
        tab2 = QtWidgets.QFrame(self.main)
        self.tab_widget.addTab(tab1, "Basic")
        self.tab_widget.addTab(tab2, "Extra")
        self.tab1_layout = QtWidgets.QGridLayout()
        self.tab1_layout.setContentsMargins(5, 0, 0, 0)
        self.tab1_layout.setVerticalSpacing(1)
        tab1.setLayout(self.tab1_layout)
        self.tab2_layout = QtWidgets.QGridLayout()
        self.tab2_layout.setContentsMargins(5, 0, 0, 0)
        self.tab2_layout.setVerticalSpacing(1)
        tab2.setLayout(self.tab2_layout)

    def _define_components_1(self):
        self.custom_potential_checkbox = QtWidgets.QCheckBox("Custom Potentials", self.main)
        self.custom_appeal_checkbox = QtWidgets.QCheckBox("Total Appeal", self.main)
        self.custom_appeal_checkbox.setToolTip("This option will ignore support appeal.")
        self.custom_support_checkbox = QtWidgets.QCheckBox("Support Appeal", self.main)
        self.custom_perfect_play_checkbox = QtWidgets.QCheckBox("Perfect Simulation", self.main)
        self.theoretical_max_checkbox = QtWidgets.QCheckBox("Theoretical Max Simulation", self.main)
        self.theoretical_max_checkbox.setToolTip("Get the highest score theoretically possible.")
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

    def _define_components_2(self):
        self.encore_amr_checkbox = QtWidgets.QCheckBox("Disable Alt/Mutual/Ref smuggling", self.main)
        self.encore_amr_checkbox.setToolTip("Force encore copied Alt/Mutual/Ref to only use cache from encore's unit.")
        self.encore_magic_unit_checkbox = QtWidgets.QCheckBox("Disable Magic smuggling", self.main)
        self.encore_magic_unit_checkbox.setToolTip("Force encore copied Magic to only copy skills from encore's unit.")
        self.encore_magic_agg_checkbox = QtWidgets.QCheckBox("Encore Magic can reso multiple boosts", self.main)
        self.encore_magic_agg_checkbox.setToolTip("Allow encore Magic to sum multiple skill boosts.")
        self.mirror_checkbox = QtWidgets.QCheckBox("Mirror", self.main)
        self.skill_boundary = QtWidgets.QComboBox(self.main)
        self.skill_boundary.setToolTip("Change the way skill detection works.")
        self.allow_great_checkbox = QtWidgets.QCheckBox("Allow GREATs in simulations", self.main)
        self.allow_great_checkbox.setToolTip("Forced for theoretical max, ignored for perfect simulations.")
        self._setup_skill_boundaries()

    def _setup_positions_1(self):
        self.tab1_layout.addWidget(self.custom_perfect_play_checkbox, 1, 0, 1, 3)
        self.tab1_layout.addWidget(self.theoretical_max_checkbox, 2, 0, 1, 3)
        self.tab1_layout.addWidget(self.custom_potential_checkbox, 1, 3, 1, 2)
        self.tab1_layout.addWidget(self.doublelife_checkbox, 2, 3, 1, 2)
        self.tab1_layout.addWidget(self.custom_support_text, 0, 5, 1, 1)
        self.tab1_layout.addWidget(self.custom_support_checkbox, 0, 6, 1, 1)
        self.tab1_layout.addWidget(self.custom_appeal_text, 1, 5, 1, 1)
        self.tab1_layout.addWidget(self.custom_appeal_checkbox, 1, 6, 1, 1)
        self.tab1_layout.addWidget(self.autoplay_offset_text, 2, 5, 1, 1)
        self.tab1_layout.addWidget(self.autoplay_mode_checkbox, 2, 6, 1, 1)
        self.tab1_layout.addWidget(self.custom_vocal, 0, 0, 1, 1)
        self.tab1_layout.addWidget(self.custom_dance, 0, 1, 1, 1)
        self.tab1_layout.addWidget(self.custom_visual, 0, 2, 1, 1)
        self.tab1_layout.addWidget(self.custom_life, 0, 3, 1, 1)
        self.tab1_layout.addWidget(self.custom_skill, 0, 4, 1, 1)

        self.tab1_layout.setColumnStretch(0, 1)
        self.tab1_layout.setColumnStretch(1, 1)
        self.tab1_layout.setColumnStretch(2, 1)
        self.tab1_layout.setColumnStretch(3, 1)
        self.tab1_layout.setColumnStretch(4, 1)
        self.tab1_layout.setColumnStretch(5, 3)
        self.tab1_layout.setColumnStretch(6, 1)

    def _setup_positions_2(self):
        self.tab2_layout.addWidget(self.encore_amr_checkbox, 0, 0, 1, 1)
        self.tab2_layout.addWidget(self.encore_magic_unit_checkbox, 1, 0, 1, 1)
        self.tab2_layout.addWidget(self.encore_magic_agg_checkbox, 2, 0, 1, 1)

        self.tab2_layout.addWidget(self.mirror_checkbox, 0, 1, 1, 1)
        self.tab2_layout.addWidget(self.skill_boundary, 1, 1, 1, 1)
        self.tab2_layout.addWidget(self.allow_great_checkbox, 2, 1, 1, 1)
        self.tab2_layout.setColumnStretch(0, 1)

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

    @subscribe(GetEncoreAMRFlagEvent)
    def get_encore_amr_checkbox_flag(self, event=None):
        return self.view.encore_amr_checkbox.isChecked()

    @subscribe(GetEncoreMagicUnitFlagEvent)
    def get_encore_magic_unit_checkbox_flag(self, event=None):
        return self.view.encore_magic_unit_checkbox.isChecked()

    @subscribe(GetEncoreMagicMaxAggEvent)
    def get_encore_magic_agg_checkbox_flag(self, event=None):
        return self.view.encore_magic_agg_checkbox.isChecked()

    @subscribe(GetSkillBoundaryEvent)
    def get_skill_boundary(self, event=None):
        if self.view.skill_boundary.currentIndex() == 0 or self.view.skill_boundary.currentIndex() == 1:
            return False, True
        if self.view.skill_boundary.currentIndex() == 2:
            return True, False
        if self.view.skill_boundary.currentIndex() == 3:
            return True, True
        return False, False

    @subscribe(GetAllowGreatEvent)
    def get_allow_great_flag(self, event=None):
        return self.view.allow_great_checkbox.isChecked()

    def hook_events(self):
        self.view.mirror_checkbox.toggled.connect(
            lambda: eventbus.eventbus.post(ToggleMirrorEvent(self.view.mirror_checkbox.isChecked())))
