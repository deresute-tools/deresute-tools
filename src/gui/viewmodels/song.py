import io
from collections import OrderedDict

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidget, QAbstractItemView, QTableWidgetItem

from settings import MUSICSCORES_PATH
from src import customlogger as logger
from src.db import db
from src.gui.viewmodels.utils import NumericalTableWidgetItem
from src.logic.live import classify_note
from src.network import meta_updater
from src.static.note_type import NoteType
from src.static.song_difficulty import Difficulty


class SongListView:
    def __init__(self, main, song_model):
        self.widget = QTableWidget(main)
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.setHorizontalScrollMode(1)  # Smooth scroll
        self.widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.widget.verticalHeader().setVisible(False)
        self.widget.setSortingEnabled(True)
        self.widget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Disable edit
        self.widget.setToolTip("Double click to select.")
        self.model = False
        self.song_model = song_model
        self.widget.cellDoubleClicked.connect(lambda r, _: self.handle_double_click(r))

    def set_model(self, model):
        self.model = model

    def load_data(self, data):
        self.widget.setColumnCount(len(data[0]) + 1)
        self.widget.setRowCount(len(data))
        self.widget.setHorizontalHeaderLabels(["No."] + list(data[0].keys()))
        for r_idx, song_data in enumerate(data):
            self.widget.setItem(r_idx, 0, NumericalTableWidgetItem(r_idx + 1))
            for c_idx, (key, value) in enumerate(song_data.items()):
                if value is None:
                    continue
                if isinstance(value, int):
                    self.widget.setItem(r_idx, c_idx + 1, NumericalTableWidgetItem(value))
                else:
                    self.widget.setItem(r_idx, c_idx + 1, QTableWidgetItem(str(value)))
        logger.info("Loaded {} songs".format(len(data)))
        self.widget.setColumnHidden(4, True)
        self.widget.horizontalHeader().setSectionResizeMode(3)  # Auto fit
        self.widget.horizontalHeader().setSectionResizeMode(1, 1)  # Auto fit

    def handle_double_click(self, r):
        chart_id = int(self.widget.item(r, 4).text())
        self.song_model.get_charts(chart_id)


class SongListModel:

    def __init__(self, view):
        self.view = view

    def initialize_songs(self):
        db.masterdb.execute("""ATTACH DATABASE "{}" AS cachedb""".format(meta_updater.get_cachedb_path()))
        db.masterdb.commit()
        data = db.masterdb.execute_and_fetchall("""
                    SELECT 
                        ld.sort as _sort,
                        ld.end_date as _end_date,
                        REPLACE(name, "\\n", "") as Name,
                        ct.text as Type,
                        bpm as BPM,
                        music_data.id as id,
                        ld.difficulty_101 as _difficulty_101
                    FROM music_data
                    INNER JOIN live_data as ld ON ld.music_data_id = music_data.id
                    INNER JOIN cachedb.color_text ct on ld.type = ct.id
                    WHERE ld.sort < 9000
                """, out_dict=True)
        db.masterdb.execute("DETACH DATABASE cachedb")
        db.masterdb.commit()

        cloned = dict()
        for value in data:
            if value['Name'] in cloned:
                if value['_end_date'] == "" and int(value['_difficulty_101']) != 0:
                    cloned[value['Name']] = value
                continue
            cloned[value['Name']] = value
        data = list(sorted(cloned.values(), key=lambda value: value['_sort']))
        for idx, value in enumerate(data):
            _sort = value.pop('_sort')
            value['_sort'] = _sort
            value.pop('_end_date')
            value.pop('id')
            value.pop('_difficulty_101')
        self.view.load_data(data)


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
        self.widget.verticalHeader().setVisible(False)
        self.widget.setSortingEnabled(False)
        self.widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.widget.setToolTip("Right click to show percentage.")
        self.model = False
        self.percentage = False

        self.widget.cellClicked.connect(lambda r, _: self.ping_support(r))

    def set_model(self, model):
        self.model = model

    def attach_support_model(self, support_model):
        self.support_model = support_model

    def load_data(self, score_id, data):
        self.widget.setColumnCount(13)
        self.widget.setRowCount(len(data))
        self.widget.setHorizontalHeaderLabels(
            ["Difficulty", "Level", "Total", "Tap", "Long", "Flick", "Slide", "Tap", "Long", "Flick", "Slide",
             "_score_id", "_diff_id"])
        for r_idx, (key, chart_data) in enumerate(data.items()):
            chart_data = list(chart_data.values())
            values = chart_data[:3]
            values.extend([_[0] for _ in chart_data[3:]])
            values.extend(["{:05.2f}%".format(_[1]) for _ in chart_data[3:]])
            for c_idx, value in enumerate(values):
                if isinstance(value, int):
                    self.widget.setItem(r_idx, c_idx, NumericalTableWidgetItem(value))
                else:
                    self.widget.setItem(r_idx, c_idx, QTableWidgetItem(str(value)))
            self.widget.setItem(r_idx, 11, NumericalTableWidgetItem(score_id))
            self.widget.setItem(r_idx, 12, NumericalTableWidgetItem(key.value))
        logger.info("Loaded {} charts".format(len(data)))
        self.widget.horizontalHeader().setSectionResizeMode(1)  # Auto fit
        self.widget.setColumnHidden(11, True)
        self.widget.setColumnHidden(12, True)
        self.toggle_percentage(change=False)

    def toggle_percentage(self, change=True):
        if change:
            self.percentage = not self.percentage
        if not self.percentage:
            for r_idx in range(7, 11):
                self.widget.setColumnHidden(r_idx, True)
            for r_idx in range(3, 7):
                self.widget.setColumnHidden(r_idx, False)
        else:
            for r_idx in range(7, 11):
                self.widget.setColumnHidden(r_idx, False)
            for r_idx in range(3, 7):
                self.widget.setColumnHidden(r_idx, True)

    def ping_support(self, r):
        song_id = int(self.widget.item(r, 11).text())
        difficulty = int(self.widget.item(r, 12).text())
        self.support_model.set_music(song_id, difficulty)
        self.support_model.generate_support()


class SongModel:

    def __init__(self, view):
        assert isinstance(view, SongView)
        self.view = view

    def get_charts(self, music_id):
        db.masterdb.execute("""ATTACH DATABASE "{}" AS cachedb""".format(meta_updater.get_cachedb_path()))
        db.masterdb.commit()
        query_results = db.masterdb.execute_and_fetchall(
            """
            SELECT
                live.difficulty_type AS sort_key,
                live.level_vocal AS level,
                live_data.id AS score_id,
                dt.text AS difficulty_text 
            FROM live_data, live_detail live
            INNER JOIN cachedb.difficulty_text dt ON dt.id = live.difficulty_type
            WHERE live_data.sort = ? AND live.live_data_id = live_data.id
            ORDER BY sort_key
            """,
            [music_id], out_dict=True
        )
        db.masterdb.execute("DETACH DATABASE cachedb")
        db.masterdb.commit()

        meta_dict = {_['sort_key']: (_['difficulty_text'], _['level']) for _ in query_results}

        score_id = query_results[0]['score_id']
        with db.CustomDB(MUSICSCORES_PATH / "musicscores_m{:03d}.db".format(score_id)) as score_conn:
            scores = score_conn.execute_and_fetchall(
                """
                SELECT * FROM blobs WHERE name LIKE "musicscores/m{:03d}/{:d}_%.csv"
                """.format(score_id, score_id)
            )

        scores = {Difficulty(int(score[0].split("_")[-1].split(".")[0])): score[1] for score in scores}
        for key, _ in scores.items():
            notes_data = pd.read_csv(io.StringIO(_.decode()))
            notes_data = notes_data[notes_data["type"] < 10].reset_index(drop=True)
            notes_data['note_type'] = notes_data.apply(classify_note, axis=1)
            total_notes = len(notes_data)
            note_count = dict(notes_data['note_type'].value_counts())
            result_dict = OrderedDict()
            result_dict['Difficulty'], result_dict['Level'] = meta_dict[int(key.value)]
            result_dict['Total'] = len(notes_data)
            for note_type in NoteType:
                key_str = note_type.name.capitalize()
                if note_type in note_count:
                    result_dict[key_str] = note_count[note_type], round(note_count[note_type] / total_notes * 100, 2)
                else:
                    result_dict[key_str] = 0, 0
            scores[key] = result_dict
        scores = OrderedDict({k: scores[k] for k in sorted(scores.keys(), key=lambda x: x.value)})
        self.view.load_data(score_id, scores)
