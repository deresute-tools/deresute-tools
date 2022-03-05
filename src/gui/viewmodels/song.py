from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QTableWidget, QAbstractItemView, QTableWidgetItem, QApplication

import customlogger as logger
from db import db
from gui.events.calculator_view_events import RequestSupportTeamEvent, SupportTeamSetMusicEvent
from gui.events.chart_viewer_events import SendMusicEvent, PopupChartViewerEvent
from gui.events.song_view_events import GetSongDetailsEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.viewmodels.mime_headers import MUSIC
from gui.viewmodels.utils import NumericalTableWidgetItem
from static.color import Color
from static.song_difficulty import Difficulty


class SongViewWidget(QTableWidget):
    def __init__(self, main, song_view, *args, **kwargs):
        super(SongViewWidget, self).__init__(main, *args, **kwargs)
        self.song_view = song_view

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            if self.song_view.shifting:
                self.song_view.toggle_timers()
            else:
                self.song_view.toggle_percentage()
            return
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.selected = self.selectedIndexes()
        super().mousePressEvent(event)

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
        mimedata.setText(MUSIC + "|".join(map(str, self.song_view.model.get_song(GetSongDetailsEvent()))))
        drag.setMimeData(mimedata)
        drag.exec_(Qt.CopyAction | Qt.MoveAction)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.song_view.shifting = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.song_view.shifting = False

class SongView:
    def __init__(self, main):
        self.widget = SongViewWidget(main, self)
        self.widget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Disable edit
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.setHorizontalScrollMode(1)  # Smooth scroll
        self.widget.verticalHeader().setVisible(False)
        self.widget.setSortingEnabled(True)
        self.widget.setDragEnabled(True)
        self.widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.widget.setToolTip("Right click to toggle note types between number and percentage.\n"
                               "Shift-right click to toggle timer percentages")
        self.model = False
        self.percentage = False
        self.timers = False
        self.shifting = False
        self.chart_viewer = None

    def set_model(self, model):
        self.model = model
        self.widget.cellClicked.connect(lambda r, _: self.model.ping_support(r))
        self.widget.cellDoubleClicked.connect(lambda r, _: self.model.popup_and_load_chart(r))

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
                     "Note Count", "7h %", "9h %", "11h %", "12m %", "6m %", "9m %", "11m %", "13h %",
                     "Tap", "Long", "Flick", "Slide", "Tap %", "Long %", "Flick %", "Slide %"]
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
        self.toggle_timers(change=False)
        self.toggle_auto_resize(True)

    def toggle_timers(self, change=True):
        if change:
            self.timers = not self.timers
        if self.timers:
            for r_idx in range(10, 18):
                self.widget.setColumnHidden(r_idx, False)
        else:
            for r_idx in range(10, 18):
                self.widget.setColumnHidden(r_idx, True)

    def toggle_percentage(self, change=True):
        if change:
            self.percentage = not self.percentage
        if not self.percentage:
            for r_idx in range(22, 26):
                self.widget.setColumnHidden(r_idx, True)
            for r_idx in range(18, 22):
                self.widget.setColumnHidden(r_idx, False)
        else:
            for r_idx in range(22, 26):
                self.widget.setColumnHidden(r_idx, False)
            for r_idx in range(18, 22):
                self.widget.setColumnHidden(r_idx, True)

    def toggle_auto_resize(self, on=False):
        if on:
            self.widget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            self.widget.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.Interactive)
        else:
            self.widget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)


class SongModel:

    def __init__(self, view):
        assert isinstance(view, SongView)
        self.view = view
        eventbus.eventbus.register(self)

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
                            ldc.Timer_7h as Timer7h,
                            ldc.Timer_9h as Timer9h,
                            ldc.Timer_11h as Timer11h,
                            ldc.Timer_12m as Timer12m,
                            ldc.Timer_6m as Timer6m,
                            ldc.Timer_9m as Timer9m, 
                            ldc.Timer_11m as Timer11m,
                            ldc.Timer_13h as Timer13h,
                            ldc.Tap as Tap,
                            ldc.Long as Long,
                            ldc.Flick as Flick,
                            ldc.Slide as Slide
                    FROM live_detail_cache as ldc
                """
        data = db.cachedb.execute_and_fetchall(query, out_dict=True)
        checked_set = set()
        id_dict = dict()
        dupe_set = set()
        for _ in data:
            if _['DifficultyInt'] != 5:
                continue
            if _['Name'] not in checked_set:
                checked_set.add(_['Name'])
                id_dict[_['Name']] = list()
            else:
                dupe_set.add(_['Name'])
            id_dict[_['Name']].append(_['LiveID'])
        to_be_hidden = [max(id_dict[dupe]) for dupe in dupe_set]
        data = [
            _ for _ in data if _['DifficultyInt'] != 5 or _['LiveID'] not in to_be_hidden
        ]
        timers = ['7h', '9h', '11h', '12m', '6m', '9m', '11m', '13h']
        for _ in data:
            _['Color'] = Color(_['Color'] - 1).name
            _['Difficulty'] = Difficulty(_['Difficulty']).name
            _['Duration'] = "{:07.3f}".format(_['Duration'])
            _['TapPct'] = "{:05.2f}%".format(_['Tap'] / _['Notes'] * 100)
            _['LongPct'] = "{:05.2f}%".format(_['Long'] / _['Notes'] * 100)
            _['FlickPct'] = "{:05.2f}%".format(_['Flick'] / _['Notes'] * 100)
            _['SlidePct'] = "{:05.2f}%".format(_['Slide'] / _['Notes'] * 100)
            for timer in timers:
                key = 'Timer' + timer
                _[key] = "{:05.2f}%".format(_[key] * 100)
        self.view.load_data(data)

    @subscribe(GetSongDetailsEvent)
    def get_song(self, event=None):
        row_idx = self.view.widget.selectionModel().currentIndex().row()
        if row_idx == -1:
            return None, None, None, None, None
        live_detail_id = int(self.view.widget.item(row_idx, 0).text())
        score_id = int(self.view.widget.item(row_idx, 1).text())
        diff_id = int(self.view.widget.item(row_idx, 2).text())
        return score_id, diff_id, live_detail_id, \
               self.view.widget.item(row_idx, 4).text(), self.view.widget.item(row_idx, 6).text()

    def ping_support(self, r):
        song_id = int(self.view.widget.item(r, 1).text())
        difficulty = int(self.view.widget.item(r, 2).text())
        eventbus.eventbus.post(SendMusicEvent(song_id, difficulty))
        eventbus.eventbus.post(SupportTeamSetMusicEvent(song_id, difficulty))
        eventbus.eventbus.post(RequestSupportTeamEvent())

    def popup_and_load_chart(self, r):
        eventbus.eventbus.post(PopupChartViewerEvent())
        song_id = int(self.view.widget.item(r, 1).text())
        difficulty = int(self.view.widget.item(r, 2).text())
        eventbus.eventbus.post(SendMusicEvent(song_id, difficulty))
