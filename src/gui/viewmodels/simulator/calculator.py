import ast
import threading
from abc import abstractmethod

import numpy as np
from PyQt5.QtCore import QSize, Qt, QMimeData
from PyQt5.QtGui import QDrag, QFont, QFontMetrics
from PyQt5.QtWidgets import QHBoxLayout, QAbstractItemView, QTableWidget, QApplication, QTableWidgetItem, \
    QWidget, QLabel, QSizePolicy, QStackedLayout, QVBoxLayout, QCheckBox

import customlogger as logger
from gui.events.calculator_view_events import GetAllCardsEvent, DisplaySimulationResultEvent, \
    AddEmptyUnitEvent, SetSupportCardsEvent, RequestSupportTeamEvent, ContextAwarePushCardEvent, \
    TurnOffRunningLabelFromUuidEvent, ToggleUnitLockingOptionsVisibilityEvent
from gui.events.chart_viewer_events import HookUnitToChartViewerEvent
from gui.events.song_view_events import GetSongDetailsEvent
from gui.events.state_change_events import AutoFlagChangeEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.events.utils.wrappers import BaseSimulationResultWithUuid
from gui.events.value_accessor_events import GetAppealsEvent, GetSupportEvent, GetUnitLockingOptionsVisibilityEvent, \
    GetCustomBonusEvent, GetGrooveSongColor
from gui.viewmodels.mime_headers import CALCULATOR_UNIT, UNIT_EDITOR_UNIT, MUSIC
from gui.viewmodels.unit import UnitView, UnitWidget
from gui.viewmodels.utils import NumericalTableWidgetItem, UniversalUniqueIdentifiable
from simulator import SimulationResult, AutoSimulationResult

UNIVERSAL_HEADERS = ["Unit", "Appeals", "Life"]
NORMAL_SIM_HEADERS = ["Perfect", "Mean", "Max", "Min", "Fans", "90%", "75%", "50%", "Theo. Max"]
AUTOPLAY_SIM_HEADERS = ["Auto Score", "Perfects", "Misses", "Max Combo", "Lowest Life", "Lowest Life Time (s)",
                        "All Skills 100%?"]
ALL_HEADERS = UNIVERSAL_HEADERS + NORMAL_SIM_HEADERS + AUTOPLAY_SIM_HEADERS

mutex = threading.Lock()


class CalculatorUnitWidgetWithExtraData(UnitWidget):
    def __init__(self, unit_view, parent=None, size=32, *args, **kwargs):
        super().__init__(unit_view, parent, size, *args, **kwargs)
        self.setAcceptDrops(True)

        self.card_widget = QWidget(self)

        self.master_layout = QVBoxLayout()

        # Abstract
        self.create_card_layout()

        self.initialize_running_label()
        self.stack_card_layout_and_running_label()
        self.initialize_song_name_label()
        self.initialize_checkboxes()
        self.lock_chart_checkbox.toggled.connect(lambda: self.toggle_lock_chart())
        self.lock_unit_checkbox.toggled.connect(lambda: self.toggle_lock_unit())

        self.setup_master_layout()

        self.setLayout(self.master_layout)
        self.toggle_running_simulation(False)
        self.running_simulation = False

        self.lock_unit = False
        self.extra_bonus = None
        self.special_option = None
        self.special_value = None

        self.lock_chart = False
        self.score_id = None
        self.diff_id = None
        self.live_detail_id = None
        self.groove_song_color = None

    @property
    def extended_cards_data(self):
        return CardsWithUnitUuidAndExtraData(self.get_uuid(),
                                             self.get_short_uuid(),
                                             self.cards_internal,
                                             self.lock_unit,
                                             self.extra_bonus,
                                             self.special_option,
                                             self.special_value,
                                             self.lock_chart,
                                             self.score_id,
                                             self.diff_id,
                                             self.live_detail_id,
                                             self.groove_song_color)

    def toggle_lock_unit(self):
        self.lock_unit = not self.lock_unit
        if not self.lock_unit:
            self.extra_bonus = None
            self.special_option = None
            self.special_value = None
            return
        extra_bonus, special_option, special_value = eventbus.eventbus.post_and_get_first(GetCustomBonusEvent())
        self.extra_bonus = extra_bonus
        self.special_option = special_option
        self.special_value = special_value

    def toggle_lock_chart(self):
        self.lock_chart = not self.lock_chart
        if not self.lock_chart:
            self.score_id = None
            self.diff_id = None
            self.live_detail_id = None
            self.groove_song_color = None
            self.song_name_label.setText("No chart loaded")
            return
        self.handle_hooked_chart(*eventbus.eventbus.post_and_get_first(GetSongDetailsEvent()))
        groove_song_color = eventbus.eventbus.post_and_get_first(GetGrooveSongColor())
        self.groove_song_color = groove_song_color

    def handle_hooked_chart(self, score_id, diff_id, live_detail_id, song_name, diff_name):
        if not self.lock_chart:
            return
        try:
            self.score_id = int(score_id)
        except:
            self.score_id = score_id
        try:
            self.diff_id = int(diff_id)
        except:
            self.diff_id = diff_id
        try:
            self.live_detail_id = int(live_detail_id)
        except:
            self.live_detail_id = live_detail_id
        string = "{} - {}".format(diff_name, song_name)
        metrics = QFontMetrics(self.song_name_label.font())
        elided_text = metrics.elidedText(string, Qt.ElideRight, self.song_name_label.width())
        self.song_name_label.setText(elided_text)

    def initialize_running_label(self):
        self.running_label = QLabel(self.card_widget)
        self.running_label.setText("Running...")
        font = QFont()
        font.setPixelSize(20)
        self.running_label.setFont(font)
        self.running_label.setAlignment(Qt.AlignCenter)
        self.running_label.setStyleSheet("background-color: rgba(255, 255, 255, 100);")
        self.running_label.setAutoFillBackground(True)

    def stack_card_layout_and_running_label(self):
        self.stacked_layout = QStackedLayout()
        self.stacked_layout.addWidget(self.card_widget)
        self.stacked_layout.addWidget(self.running_label)
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_layout.setStackingMode(QStackedLayout.StackAll)

    def initialize_song_name_label(self):
        self.song_name_label = QLabel(self)
        self.song_name_label.setText("No chart loaded")
        self.song_name_label.setAlignment(Qt.AlignCenter)

    def initialize_checkboxes(self):
        self.checkbox_container_widget = QWidget(self)
        checkbox_layout = QHBoxLayout()
        self.lock_chart_checkbox = QCheckBox("Lock Chart")
        self.lock_unit_checkbox = QCheckBox("Lock Unit")
        checkbox_layout.addWidget(self.lock_chart_checkbox)
        checkbox_layout.addWidget(self.lock_unit_checkbox)
        checkbox_layout.setAlignment(Qt.AlignCenter)
        self.checkbox_container_widget.setLayout(checkbox_layout)

    def setup_master_layout(self):
        self.master_layout.addLayout(self.stacked_layout)
        self.master_layout.addWidget(self.song_name_label)
        self.master_layout.addWidget(self.checkbox_container_widget)
        self.master_layout.setContentsMargins(3, 3, 3, 3)
        self.master_layout.setSpacing(1)
        state = eventbus.eventbus.post_and_get_first(GetUnitLockingOptionsVisibilityEvent())
        self.song_name_label.setVisible(state)
        self.checkbox_container_widget.setVisible(state)

    def toggle_running_simulation(self, running=False):
        self.running_label.setVisible(running)
        self.running_simulation = running

    @abstractmethod
    def create_card_layout(self):
        pass

    def toggle_unit_locking_options_visibility(self, flag):
        self.song_name_label.setVisible(flag)
        self.checkbox_container_widget.setVisible(flag)

    def dragEnterEvent(self, e):
        e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        mimetext = e.mimeData().text()
        if mimetext.startswith(MUSIC):
            logger.debug("Dragged {} into unit".format(mimetext))
            self.handle_hooked_chart(*mimetext[len(MUSIC):].split("|"))
        else:
            if type(self.unit_view.widget) == DroppableCalculatorWidget:
                self.unit_view.widget.handle_lost_mime(mimetext)


class CalculatorUnitWidget(CalculatorUnitWidgetWithExtraData, UniversalUniqueIdentifiable):
    def __init__(self, unit_view, parent=None, size=32):
        super(CalculatorUnitWidget, self).__init__(unit_view, parent, size)

    def handle_lost_mime(self, mime_text):
        if type(self.unit_view) == UnitView:
            self.unit_view.handle_lost_mime(mime_text)

    def create_card_layout(self):
        self.card_widget = QWidget(self)
        self.cardLayout = QHBoxLayout()
        for idx, card in enumerate(self.cards):
            card.setMinimumSize(QSize(self.icon_size + 2, self.icon_size + 2))
            self.cardLayout.addWidget(card)
        self.card_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.card_widget.setLayout(self.cardLayout)


class DroppableCalculatorWidget(QTableWidget):
    def __init__(self, calculator_view, *args, **kwargs):
        super(DroppableCalculatorWidget, self).__init__(*args, **kwargs)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setStyleSheet(
            "QTableWidget::item:selected{ background-color: rgba(50, 115, 220, 0.15); color: rgb(0,0,0); }")
        self.calculator_view = calculator_view

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.calculator_view.delete_unit()
        if QApplication.keyboardModifiers() == (Qt.ShiftModifier | Qt.ControlModifier) and event.key() == Qt.Key_D:
            self.calculator_view.duplicate_unit(True)
        elif QApplication.keyboardModifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
            self.calculator_view.duplicate_unit(False)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.selected = self.selectedIndexes()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        if self.selectedItems():
            self.selected = self.selectedIndexes()
        if not self.selected:
            return
        drag = QDrag(self)
        mimedata = QMimeData()
        mimedata.setText(CALCULATOR_UNIT + str(self.cellWidget(self.selected[0].row(), 0).card_ids))
        drag.setMimeData(mimedata)
        drag.exec_(Qt.CopyAction | Qt.MoveAction)

    def dragEnterEvent(self, e):
        e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        mimetext = e.mimeData().text()
        if mimetext.startswith(UNIT_EDITOR_UNIT):
            card_ids = ast.literal_eval(mimetext[len(UNIT_EDITOR_UNIT):])
            logger.debug("Dragged {} into calculator".format(card_ids))
            self.calculator_view.add_unit(card_ids)
        else:
            e.acceptProposedAction()

    def handle_lost_mime(self, mimetext):
        card_ids = ast.literal_eval(mimetext[len(UNIT_EDITOR_UNIT):])
        logger.debug("Dragged {} into calculator".format(card_ids))
        self.calculator_view.add_unit(card_ids)


class CalculatorView:
    def __init__(self, main, main_view):
        self.main_view = main_view
        self.initialize_widget(main)
        self.setup_widget()

    def initialize_widget(self, main):
        self.widget = DroppableCalculatorWidget(self, main)

    def setup_widget(self):
        self.widget.setHorizontalScrollMode(1)  # Smooth scroll
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.setColumnCount(len(ALL_HEADERS))
        self.widget.setRowCount(0)
        self.widget.verticalHeader().setDefaultSectionSize(75)
        self.widget.verticalHeader().setSectionResizeMode(3)
        self.widget.horizontalHeader().setSectionResizeMode(3)  # Auto fit
        self.widget.setHorizontalHeaderLabels(ALL_HEADERS)
        self.widget.setColumnWidth(0, 40 * 6)
        self.toggle_auto(False)

        self.widget.cellClicked.connect(lambda r, _: self.handle_unit_click(r))
        self.widget.cellDoubleClicked.connect(lambda r, _: self.main_view.simulate(r))

    def toggle_auto(self, auto_flag=True):
        if auto_flag:
            for r_idx in range(len(UNIVERSAL_HEADERS) + len(NORMAL_SIM_HEADERS), len(ALL_HEADERS) + 1):
                self.widget.setColumnHidden(r_idx, False)
            for r_idx in range(len(UNIVERSAL_HEADERS), len(UNIVERSAL_HEADERS) + len(NORMAL_SIM_HEADERS)):
                self.widget.setColumnHidden(r_idx, True)
        else:
            for r_idx in range(len(UNIVERSAL_HEADERS) + len(NORMAL_SIM_HEADERS), len(ALL_HEADERS) + 1):
                self.widget.setColumnHidden(r_idx, True)
            for r_idx in range(len(UNIVERSAL_HEADERS), len(UNIVERSAL_HEADERS) + len(NORMAL_SIM_HEADERS)):
                self.widget.setColumnHidden(r_idx, False)

    def set_model(self, model):
        self.model = model

    def insert_unit(self):
        self.widget.insertRow(self.widget.rowCount())
        simulator_unit_widget = CalculatorUnitWidget(self, None, size=32)
        self.widget.setCellWidget(self.widget.rowCount() - 1, 0, simulator_unit_widget)
        logger.debug("Inserted empty unit at {}".format(self.widget.rowCount()))
        self.widget.setColumnWidth(0, 40 * 6)
        self.widget.setRowHeight(self.widget.rowCount() - 1, 300)

    def delete_unit(self):
        if len(self.widget.selectionModel().selectedRows()) == 0:
            return
        selected_row = self.widget.selectionModel().selectedRows()[0].row()
        self.widget.removeRow(selected_row)

    def duplicate_unit(self, custom_card_data=False):
        selected_row = self.widget.selectionModel().selectedRows()[0].row()
        cell_widget = self.widget.cellWidget(selected_row, 0)
        card_ids = cell_widget.card_ids
        self.add_unit(card_ids)
        if custom_card_data:
            cloned_card_internals = cell_widget.clone_internal()
            new_unit = self.widget.cellWidget(self.widget.rowCount() - 1, 0)
            new_unit.cards_internal = cloned_card_internals
            for card in cloned_card_internals:
                if card is None:
                    continue
                card.refresh_values()

    def set_unit(self, cards, row=None):
        if row is None:
            row = self.widget.rowCount() - 1
        for idx, card in enumerate(cards):
            if card is None:
                continue
            self.widget.cellWidget(row, 0).set_card(idx=idx, card=card)
        logger.info("Unit insert: {} - {} row {}".format(self.widget.cellWidget(row, 0).get_short_uuid(),
                                                         " ".join(map(str, cards)), row))

    def add_unit(self, cards):
        if len(cards) == 15:
            for _ in range(3):
                self.add_unit_int(cards[_ * 5: (_ + 1) * 5])
        else:
            self.add_unit_int(cards)

    def add_unit_int(self, cards):
        for r in range(self.widget.rowCount()):
            if self.widget.cellWidget(r, 0).card_ids == [None] * 6:
                logger.debug("Empty calculator unit at row {}".format(r))
                self.set_unit(row=r, cards=cards)
                return
        self.model.add_empty_unit(AddEmptyUnitEvent(self.model))
        self.set_unit(row=self.widget.rowCount() - 1, cards=cards)

    def create_support_team(self, r):
        if not eventbus.eventbus.post_and_get_first(
                SetSupportCardsEvent(self.widget.cellWidget(r, 0).extended_cards_data)):
            logger.info("Invalid unit to evaluate support team")
            return
        appeals, support, life = eventbus.eventbus.post_and_get_first(RequestSupportTeamEvent())
        self.widget.setItem(r, 2, NumericalTableWidgetItem(int(life)))
        total_appeals = eventbus.eventbus.post_and_get_first(GetAppealsEvent())
        if total_appeals is not None:
            self.widget.setItem(r, 1, NumericalTableWidgetItem(total_appeals))
            return
        custom_support = eventbus.eventbus.post_and_get_first(GetSupportEvent())
        if custom_support is not None:
            support = custom_support
        self.widget.setItem(r, 1, NumericalTableWidgetItem(int(appeals + support)))

    def fill_column(self, autoplay, c, row, value):
        if c >= len(UNIVERSAL_HEADERS) - 1 and autoplay:
            column = c + 1 + len(NORMAL_SIM_HEADERS)
        else:
            column = c + 1
        if isinstance(value, int) or isinstance(value, float):
            self.widget.setItem(row, column, NumericalTableWidgetItem(value))
        else:
            self.widget.setItem(row, column, QTableWidgetItem(value))

    def clear_results(self):
        for r in range(self.widget.rowCount()):
            for c in range(len(ALL_HEADERS) - 1):
                self.widget.removeCellWidget(r, c + 1)

    def handle_unit_click(self, r):
        eventbus.eventbus.post(HookUnitToChartViewerEvent(self.widget.cellWidget(r, 0).cards_internal))
        self.create_support_team(r)


class CalculatorModel:
    view: CalculatorView

    def __init__(self, view):
        self.view = view
        eventbus.eventbus.register(self)
        self.unit_locking_options_visibility = True
        self.add_empty_unit(AddEmptyUnitEvent(self))

    @subscribe(AutoFlagChangeEvent)
    def toggle_auto(self, event):
        self.view.toggle_auto(event.flag)

    @subscribe(GetAllCardsEvent)
    def get_all_cards(self, event):
        if event.model is not self:
            return
        res = list()
        rows_to_search = range(self.view.widget.rowCount()) if event.row is None else [event.row]
        for r_idx in rows_to_search:
            unit_widget = self.view.widget.cellWidget(r_idx, 0)
            if unit_widget.running_simulation:
                logger.info("Simulation already running: {}".format(
                    unit_widget.get_uuid()))
                continue
            unit_widget.toggle_running_simulation(True)
            res.append(self.view.widget.cellWidget(r_idx, 0).extended_cards_data)
        return res

    @subscribe(DisplaySimulationResultEvent)
    def display_simulation_result(self, event):
        payload: BaseSimulationResultWithUuid = event.payload

        row_to_change = self.get_row_from_uuid(payload.uuid)

        if row_to_change == -1:
            return
        self.view.widget.cellWidget(row_to_change, 0).toggle_running_simulation(False)

        self.view.widget.setSortingEnabled(False)
        if isinstance(payload.results, SimulationResult):
            self._process_normal_results(payload.results, row_to_change)
        elif isinstance(payload.results, AutoSimulationResult):
            self._process_auto_results(payload.results, row_to_change)
        self.view.widget.setSortingEnabled(True)

    def get_row_from_uuid(self, check_uuid):
        row_to_change = -1
        for r in range(self.view.widget.rowCount()):
            uuid = self.view.widget.cellWidget(r, 0).get_uuid()
            if uuid == check_uuid:
                row_to_change = r
                break
        return row_to_change

    @subscribe(TurnOffRunningLabelFromUuidEvent)
    def turn_off_running_label_from_uuid(self, event):
        row_to_change = self.get_row_from_uuid(event.uuid)
        if row_to_change == -1:
            return
        self.view.widget.cellWidget(row_to_change, 0).toggle_running_simulation(False)

    @subscribe(AddEmptyUnitEvent)
    def add_empty_unit(self, event):
        if event.active_tab is not self:
            return
        self.view.insert_unit()

    @subscribe(ContextAwarePushCardEvent)
    def push_card_int(self, event: ContextAwarePushCardEvent):
        if event.model is not self:
            return
        inner_event = event.event
        skip_guest_push = inner_event.skip_guest_push
        card_id = inner_event.card_id
        for row in range(self.view.widget.rowCount()):
            cell_widget = self.view.widget.cellWidget(row, 0)
            card_ids = cell_widget.card_ids
            if skip_guest_push and len(card_ids) == 6:
                card_ids = card_ids[:5]
            for c_idx, card in enumerate(card_ids):
                if card is None:
                    cell_widget.set_card(idx=c_idx, card=card_id)
                    return
        self.view.add_unit([card_id, None, None, None, None, None])

    @subscribe(ToggleUnitLockingOptionsVisibilityEvent)
    def toggle_unit_locking_options_visibility(self, event):
        self.unit_locking_options_visibility = not self.unit_locking_options_visibility
        for row in range(self.view.widget.rowCount()):
            cell_widget = self.view.widget.cellWidget(row, 0)
            cell_widget.toggle_unit_locking_options_visibility(self.unit_locking_options_visibility)
        self.view.widget.verticalHeader().setSectionResizeMode(3)

    @subscribe(GetUnitLockingOptionsVisibilityEvent)
    def get_unit_locking_options_visibility(self, event):
        return self.unit_locking_options_visibility

    def _process_normal_results(self, results: SimulationResult, row=None):
        # ["Perfect", "Mean", "Max", "Min", "Fans", "Theoretical Max", "90%", "75%", "50%"])
        self.view.fill_column(False, 0, row, int(results.total_appeal))
        self.view.fill_column(False, 1, row, int(results.total_life))
        self.view.fill_column(False, 2, row, int(results.perfect_score))
        self.view.fill_column(False, 3, row, int(results.base))
        self.view.fill_column(False, 4, row, int(results.base + results.deltas.max()))
        self.view.fill_column(False, 5, row, int(results.base + results.deltas.min()))
        self.view.fill_column(False, 6, row, int(results.fans))
        self.view.fill_column(False, 7, row, int(results.base + np.percentile(results.deltas, 90)))
        self.view.fill_column(False, 8, row, int(results.base + np.percentile(results.deltas, 75)))
        self.view.fill_column(False, 9, row, int(results.base + np.percentile(results.deltas, 50)))
        if results.max_theoretical_result is not None:
            self.view.fill_column(False, 10, row, int(results.max_theoretical_result.max_score))

    def _process_auto_results(self, results: AutoSimulationResult, row=None):
        # ["Auto Score", "Perfects", "Misses", "Max Combo", "Lowest Life", "Lowest Life Time", "All Skills 100%?"]
        self.view.fill_column(True, 0, row, int(results.total_appeal))
        self.view.fill_column(True, 1, row, int(results.total_life))
        self.view.fill_column(True, 2, row, int(results.score))
        self.view.fill_column(True, 3, row, int(results.perfects))
        self.view.fill_column(True, 4, row, int(results.misses))
        self.view.fill_column(True, 5, row, int(results.max_combo))
        self.view.fill_column(True, 6, row, int(results.lowest_life))
        self.view.fill_column(True, 7, row, float(results.lowest_life_time))
        self.view.fill_column(True, 8, row, "Yes" if results.all_100 else "No")


class CardsWithUnitUuidAndExtraData:
    def __init__(self, uuid, short_uuid, cards,
                 lock_unit, extra_bonus, special_option, special_value,
                 lock_chart, score_id, diff_id, live_detail_id,
                 groove_song_color):
        self.uuid = uuid
        self.short_uuid = short_uuid
        self.cards = cards

        self.lock_unit = lock_unit
        self.extra_bonus = extra_bonus
        self.special_option = special_option
        self.special_value = special_value

        self.lock_chart = lock_chart
        self.score_id = score_id
        self.diff_id = diff_id
        self.live_detail_id = live_detail_id
        self.groove_song_color = groove_song_color
