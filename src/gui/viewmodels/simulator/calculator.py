import ast

import numpy as np
from PyQt5.QtCore import QSize, Qt, QMimeData
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QAbstractItemView, QTableWidget, QApplication, QTableWidgetItem

import customlogger as logger
from gui.events.calculator_view_events import GetAllCardsEvent, DisplaySimulationResultEvent, \
    AddEmptyUnitEvent, SetSupportCardsEvent, RequestSupportTeamEvent, ContextAwarePushCardEvent
from gui.events.chart_viewer_events import HookUnitToChartViewerEvent
from gui.events.state_change_events import AutoFlagChangeEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.events.utils.wrappers import BaseSimulationResultWithUuid
from gui.events.value_accessor_events import GetAppealsEvent, GetSupportEvent
from gui.viewmodels.mime_headers import CALCULATOR_UNIT, UNIT_EDITOR_UNIT
from gui.viewmodels.unit import UnitWidget, UnitView
from gui.viewmodels.utils import NumericalTableWidgetItem, UniversalUniqueIdentifiable
from simulator import SimulationResult, MaxSimulationResult, AutoSimulationResult

UNIVERSAL_HEADERS = ["Unit", "Appeals", "Life"]
NORMAL_SIM_HEADERS = ["Perfect", "Mean", "Max", "Min", "Fans", "Skill Off%", "90%", "75%", "50%"]
AUTOPLAY_SIM_HEADERS = ["Auto Score", "Perfects", "Misses", "Max Combo", "Lowest Life", "Lowest Life Time (s)",
                        "All Skills 100%?"]
ALL_HEADERS = UNIVERSAL_HEADERS + NORMAL_SIM_HEADERS + AUTOPLAY_SIM_HEADERS


class CalculatorUnitWidget(UnitWidget, UniversalUniqueIdentifiable):
    def __init__(self, unit_view, parent=None, size=32):
        super(CalculatorUnitWidget, self).__init__(unit_view, parent, size)
        self.verticalLayout = QVBoxLayout()
        self.cardLayout = QHBoxLayout()

        for idx, card in enumerate(self.cards):
            card.setMinimumSize(QSize(self.size + 2, self.size + 2))
            self.cardLayout.addWidget(card)

        self.verticalLayout.addLayout(self.cardLayout)
        self.setLayout(self.verticalLayout)

    def handle_lost_mime(self, mime_text):
        if type(self.unit_view) == UnitView:
            self.unit_view.handle_lost_mime(mime_text)


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
        self.widget.verticalHeader().setDefaultSectionSize(50)
        self.widget.verticalHeader().setSectionResizeMode(2)
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

    def delete_unit(self):
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
        logger.info("Inserted unit {} at row {}".format(cards, row))

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
        if not eventbus.eventbus.post_and_get_first(SetSupportCardsEvent(self.widget.cellWidget(r, 0).cards_internal)):
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
        self.add_empty_unit(AddEmptyUnitEvent(self))

    @subscribe(AutoFlagChangeEvent)
    def toggle_auto(self, event):
        self.view.toggle_auto(event.flag)

    @subscribe(GetAllCardsEvent)
    def get_all_cards(self, event=None):
        return [
            CardsWithUnitUuid(self.view.widget.cellWidget(r_idx, 0).uuid,
                              self.view.widget.cellWidget(r_idx, 0).cards_internal)
            for r_idx in range(self.view.widget.rowCount())
        ]

    @subscribe(DisplaySimulationResultEvent)
    def display_simulation_result(self, event):
        payload: BaseSimulationResultWithUuid = event.payload
        row_to_change = -1
        for r in range(self.view.widget.rowCount()):
            uuid = self.view.widget.cellWidget(r, 0).uuid
            if uuid == payload.uuid:
                row_to_change = r
                break
        if row_to_change == -1:
            return
        if isinstance(payload.results, SimulationResult):
            self._process_normal_results(payload.results, row_to_change)
        elif isinstance(payload.results, MaxSimulationResult):
            self._process_max_results(payload.results, row_to_change)
        elif isinstance(payload.results, AutoSimulationResult):
            self._process_auto_results(payload.results, row_to_change)

    @subscribe(AddEmptyUnitEvent)
    def add_empty_unit(self, event):
        if event.active_tab is not self:
            return
        self.view.insert_unit()

    @subscribe(ContextAwarePushCardEvent)
    def push_card_int(self, event: ContextAwarePushCardEvent):
        if event.model is not self:
            return
        card_id = event.card_id
        for row in range(self.view.widget.rowCount()):
            cell_widget = self.view.widget.cellWidget(row, 0)
            card_ids = cell_widget.card_ids
            for c_idx, card in enumerate(card_ids):
                if card is None:
                    cell_widget.set_card(idx=c_idx, card=card_id)
                    return
        self.view.add_unit([card_id, None, None, None, None, None])

    def _process_normal_results(self, results: SimulationResult, row=None):
        # ["Perfect", "Mean", "Max", "Min", "Fans", "Skill Off%", "90%", "75%", "50%"])
        self.view.fill_column(False, 0, row, int(results.total_appeal))
        self.view.fill_column(False, 1, row, int(results.total_life))
        self.view.fill_column(False, 2, row, int(results.perfect_score))
        self.view.fill_column(False, 3, row, int(results.base))
        self.view.fill_column(False, 4, row, int(results.base + results.deltas.max()))
        self.view.fill_column(False, 5, row, int(results.base + results.deltas.min()))
        self.view.fill_column(False, 6, row, int(results.fans))
        self.view.fill_column(False, 7, row, int(results.skill_off))
        self.view.fill_column(False, 8, row, int(results.base + np.percentile(results.deltas, 90)))
        self.view.fill_column(False, 9, row, int(results.base + np.percentile(results.deltas, 75)))
        self.view.fill_column(False, 10, row, int(results.base + np.percentile(results.deltas, 50)))

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

    def _process_max_results(self, results: MaxSimulationResult, row=None):
        self.view.fill_column(False, 0, row, int(results.total_appeal))
        self.view.fill_column(False, 1, row, int(results.total_life))
        self.view.fill_column(False, 2, row, int(results.total_perfect))
        self.view.fill_column(False, 3, row, int(results.total_perfect + results.deltas.sum()))
        self.view.fill_column(False, 4, row, 0)
        self.view.fill_column(False, 5, row, 0)
        self.view.fill_column(False, 6, row, 0)
        self.view.fill_column(False, 7, row, 0)
        self.view.fill_column(False, 8, row, 0)
        self.view.fill_column(False, 9, row, 0)


class CardsWithUnitUuid:
    def __init__(self, uuid, cards):
        self.uuid = uuid
        self.cards = cards
