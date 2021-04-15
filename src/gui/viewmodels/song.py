from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidget, QAbstractItemView, QTableWidgetItem, QMainWindow, QApplication

import customlogger as logger
from chart_pic_generator import BaseChartPicGenerator
from db import db
from gui.events.ChartViewerEvents import HookUnitToChartViewerEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.viewmodels.utils import NumericalTableWidgetItem
from logic.grandunit import GrandUnit
from logic.unit import Unit
from static.color import Color
from static.song_difficulty import Difficulty


class SongViewWidget(QTableWidget):
    def __init__(self, main, song_view, *args, **kwargs):
        super(SongViewWidget, self).__init__(main, *args, **kwargs)
        self.song_view = song_view

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.song_view.toggle_percentage()
            return
        super().mousePressEvent(event)


class SongView:
    def __init__(self, main):
        self.widget = SongViewWidget(main, self)
        self.widget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Disable edit
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.setHorizontalScrollMode(1)  # Smooth scroll
        self.widget.verticalHeader().setVisible(False)
        self.widget.setSortingEnabled(True)
        self.widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.widget.setToolTip("Right click to show percentage.")
        self.model = False
        self.percentage = False

        self.widget.cellClicked.connect(lambda r, _: self.ping_support(r))
        self.widget.cellDoubleClicked.connect(lambda r, _: self.popup_chart(r))
        self.chart_viewer = None

    def set_model(self, model):
        self.model = model

    def attach_support_model(self, support_model):
        self.support_model = support_model

    def show_only_ids(self, live_detail_ids):
        if not live_detail_ids:
            live_detail_ids = set()
        else:
            live_detail_ids = set(live_detail_ids)
        for r_idx in range(self.widget.rowCount()):
            if int(self.widget.item(r_idx, 0).text()) in live_detail_ids:
                self.widget.setRowHidden(r_idx, False)
            else:
                self.widget.setRowHidden(r_idx, True)

    def load_data(self, data):
        DATA_COLS = ["LDID", "LiveID", "DifficultyInt", "ID", "Name", "Color", "Difficulty", "Level", "Duration (s)",
                     "Note Count", "Tap", "Long", "Flick", "Slide", "Tap %", "Long %", "Flick %", "Slide %"]
        self.widget.setColumnCount(len(DATA_COLS))
        self.widget.setRowCount(len(data))
        self.widget.setHorizontalHeaderLabels(DATA_COLS)
        self.widget.setSortingEnabled(True)
        for r_idx, card_data in enumerate(data):
            for c_idx, (key, value) in enumerate(card_data.items()):
                if isinstance(value, int) and 13 >= c_idx >= 7 or c_idx == 1:
                    item = NumericalTableWidgetItem(value)
                elif value is None:
                    item = QTableWidgetItem("")
                else:
                    item = QTableWidgetItem(str(value))
                self.widget.setItem(r_idx, c_idx, item)
        logger.info("Loaded {} charts".format(len(data)))
        self.widget.setColumnHidden(0, True)
        self.widget.setColumnHidden(2, True)
        self.widget.setSortingEnabled(True)
        self.widget.sortItems(3, Qt.AscendingOrder)
        self.toggle_percentage(change=False)
        self.toggle_auto_resize(True)

    def toggle_percentage(self, change=True):
        if change:
            self.percentage = not self.percentage
        if not self.percentage:
            for r_idx in range(14, 18):
                self.widget.setColumnHidden(r_idx, True)
            for r_idx in range(10, 14):
                self.widget.setColumnHidden(r_idx, False)
        else:
            for r_idx in range(14, 18):
                self.widget.setColumnHidden(r_idx, False)
            for r_idx in range(10, 14):
                self.widget.setColumnHidden(r_idx, True)

    def ping_support(self, r):
        song_id = int(self.widget.item(r, 1).text())
        difficulty = int(self.widget.item(r, 2).text())
        self.support_model.set_music(song_id, difficulty)
        self.support_model.generate_support()

    def popup_chart(self, r):
        song_id = int(self.widget.item(r, 1).text())
        difficulty = int(self.widget.item(r, 2).text())
        if self.chart_viewer is not None:
            self.chart_viewer.destroy()
        self.chart_viewer = ChartViewer(song_id=song_id, difficulty=difficulty)

    def toggle_auto_resize(self, on=False):
        if on:
            self.widget.horizontalHeader().setSectionResizeMode(3)  # Auto fit
            self.widget.horizontalHeader().setSectionResizeMode(4, 1)  # Auto fit
        else:
            self.widget.horizontalHeader().setSectionResizeMode(0)  # Resize


class ChartViewer(QMainWindow):
    def __init__(self, song_id, difficulty, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generator = BaseChartPicGenerator.getGenerator(song_id, difficulty, self)
        eventbus.eventbus.register(self)
        self.show()

    def hook_simulation_results(self, all_cards, results, song_id, difficulty):
        self.generator = BaseChartPicGenerator.getGenerator(song_id, difficulty, self)
        self.generator.hook_simulation_results(all_cards, results)

    @subscribe(HookUnitToChartViewerEvent)
    def hook_unit(self, event: HookUnitToChartViewerEvent):
        if len(event.cards) == 15:
            unit = GrandUnit.from_list(event.cards)
        else:
            unit = Unit.from_list(event.cards)
        self.generator.set_unit(unit)

    def keyPressEvent(self, event):
        key = event.key()
        if QApplication.keyboardModifiers() == Qt.ControlModifier and key == Qt.Key_S:
            self.generator.save_image()


class SongModel:

    def __init__(self, view):
        assert isinstance(view, SongView)
        self.view = view

    def initialize_data(self):
        query = """
                    SELECT  ldc.live_detail_id as LDID,
                            ldc.live_id as LiveID,
                            ldc.difficulty as DifficultyInt,
                            ldc.sort as ID,
                            ldc.name as Name,
                            ldc.color as Color,
                            ldc.difficulty as Difficulty,
                            ldc.level as Level,
                            ldc.duration as Duration,
                            CAST(ldc.Tap + ldc.Long + ldc.Flick + ldc.Slide AS INTEGER) as Notes,
                            ldc.Tap as Tap,
                            ldc.Long as Long,
                            ldc.Flick as Flick,
                            ldc.Slide as Slide
                    FROM live_detail_cache as ldc
                """
        data = db.cachedb.execute_and_fetchall(query, out_dict=True)
        for _ in data:
            _['Color'] = Color(_['Color'] - 1).name
            _['Difficulty'] = Difficulty(_['Difficulty']).name
            _['Duration'] = "{:07.3f}".format(_['Duration'])
            _['TapPct'] = "{:05.2f}%".format(_['Tap'] / _['Notes'] * 100)
            _['LongPct'] = "{:05.2f}%".format(_['Long'] / _['Notes'] * 100)
            _['FlickPct'] = "{:05.2f}%".format(_['Flick'] / _['Notes'] * 100)
            _['SlidePct'] = "{:05.2f}%".format(_['Slide'] / _['Notes'] * 100)
        self.view.load_data(data)
