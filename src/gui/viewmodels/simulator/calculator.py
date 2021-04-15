import ast

from PyQt5.QtCore import QSize, Qt, QMimeData
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QAbstractItemView, QTableWidget, QApplication, QTableWidgetItem

import customlogger as logger
from gui.events.chart_viewer_events import HookUnitToChartViewerEvent
from gui.events.utils import eventbus
from gui.viewmodels.mime_headers import CALCULATOR_UNIT, UNIT_EDITOR_UNIT
from gui.viewmodels.unit import UnitWidget, UnitView
from gui.viewmodels.utils import NumericalTableWidgetItem
from network.api_client import get_top_build

UNIVERSAL_HEADERS = ["Unit", "Appeals", "Life"]
NORMAL_SIM_HEADERS = ["Perfect", "Mean", "Max", "Min", "Skill Off", "5%", "25%", "50%", "75%"]
AUTOPLAY_SIM_HEADERS = ["Auto Score", "Perfects", "Misses", "Max Combo", "Lowest Life", "Lowest Life Time (s)",
                        "All Skills 100%?"]
ALL_HEADERS = UNIVERSAL_HEADERS + NORMAL_SIM_HEADERS + AUTOPLAY_SIM_HEADERS


class CalculatorUnitWidget(UnitWidget):
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
        self.auto_view = False
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
        self.add_empty_unit()

    def toggle_auto(self, change=True):
        if change:
            self.auto_view = not self.auto_view
        if not self.auto_view:
            for r_idx in range(len(UNIVERSAL_HEADERS) + len(NORMAL_SIM_HEADERS), len(ALL_HEADERS) + 1):
                self.widget.setColumnHidden(r_idx, True)
            for r_idx in range(len(UNIVERSAL_HEADERS), len(UNIVERSAL_HEADERS) + len(NORMAL_SIM_HEADERS)):
                self.widget.setColumnHidden(r_idx, False)
        else:
            for r_idx in range(len(UNIVERSAL_HEADERS) + len(NORMAL_SIM_HEADERS), len(ALL_HEADERS) + 1):
                self.widget.setColumnHidden(r_idx, False)
            for r_idx in range(len(UNIVERSAL_HEADERS), len(UNIVERSAL_HEADERS) + len(NORMAL_SIM_HEADERS)):
                self.widget.setColumnHidden(r_idx, True)

    def set_support_model(self, support_model):
        self.support_model = support_model

    def attach_custom_settings_model(self, custom_settings_model):
        self.custom_settings_model = custom_settings_model
        try:
            self.custom_settings_model.view.autoplay_mode_checkbox.stateChanged.disconnect()
        except:
            pass
        self.auto_view = self.custom_settings_model.view.autoplay_mode_checkbox.isChecked()
        self.toggle_auto(False)
        trigger = lambda: self.toggle_auto(True)
        self.custom_settings_model.view.autoplay_mode_checkbox.stateChanged.connect(trigger)

    def set_model(self, model):
        self.model = model

    def add_empty_unit(self):
        simulator_unit_widget = CalculatorUnitWidget(self, self.widget, size=32)
        self._insert_unit_int(simulator_unit_widget)

    def _insert_unit_int(self, simulator_unit_widget):
        self.widget.insertRow(self.widget.rowCount())
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

    def yoink_unit(self):
        _, _, live_detail_id = self.main_view.get_song()
        try:
            cards, support = get_top_build(live_detail_id)
        except:
            return
        self.custom_settings_model.disable_custom_pots()
        self.add_unit(cards)
        self.custom_settings_model.set_support(support)
        self.custom_settings_model.enable_custom_support()

    def push_card(self, card_id):
        for row in range(self.widget.rowCount()):
            cell_widget = self.widget.cellWidget(row, 0)
            card_ids = cell_widget.card_ids
            for c_idx, card in enumerate(card_ids):
                if card is None:
                    cell_widget.set_card(idx=c_idx, card=card_id)
                    return
        self.add_unit([card_id, None, None, None, None, None])

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
        self.add_empty_unit()
        self.set_unit(row=self.widget.rowCount() - 1, cards=cards)

    def create_support_team(self, r):
        if not self.support_model.set_cards(self.widget.cellWidget(r, 0).cards_internal):
            logger.info("Invalid unit to evaluate support team")
            return
        appeals, support, life = self.support_model.generate_support()
        self.widget.setItem(r, 2, NumericalTableWidgetItem(int(life)))
        if self.custom_settings_model.get_appeals() is not None:
            self.widget.setItem(r, 1, NumericalTableWidgetItem(int(self.custom_settings_model.get_appeals())))
            return
        if self.custom_settings_model.get_support() is not None:
            support = int(self.custom_settings_model.get_support())
        self.widget.setItem(r, 1, NumericalTableWidgetItem(int(appeals + support)))

    def display_results(self, results, row, autoplay):
        if len(results) == 0:
            return
        if row is not None and results[0] is not None:
            for c, value in enumerate(results[0]):
                self._fillcolumn(autoplay, c, row, value)
            return
        for r, data in enumerate(results):
            if data is None:
                continue
            for c, value in enumerate(data):
                self._fillcolumn(autoplay, c, r, value)

    def _fillcolumn(self, autoplay, c, row, value):
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
        eventbus.eventbus.post(HookUnitToChartViewerEvent(self.widget.cellWidget(r, 0).cards_internal),
                               asynchronous=False)
        self.create_support_team(r)


class CalculatorModel:
    view: CalculatorView

    def __init__(self, view):
        self.view = view

    def get_all_cards(self):
        return [
            self.view.widget.cellWidget(r_idx, 0).cards_internal
            for r_idx in range(self.view.widget.rowCount())
        ]
