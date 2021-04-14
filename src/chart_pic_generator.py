import os
import sys
from collections import defaultdict
from math import ceil

import numpy as np
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QFont, QBrush, QPainterPath
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QScrollArea

from logic.live import fetch_chart, Live
from logic.unit import Unit
from settings import RHYTHM_ICONS_PATH
from simulator import Simulator
from static.note_type import NoteType
from static.skill import SKILL_BASE
from static.song_difficulty import Difficulty

SEC_HEIGHT = 500
LANE_DISTANCE = 70
SKILL_PAINT_WIDTH = 60
X_MARGIN = 70
Y_MARGIN = 70
RIGHT_MARGIN = 75
MAX_Y = 5000
MAX_SECS_PER_GROUP = (MAX_Y - Y_MARGIN * 2) // SEC_HEIGHT

NOTE_PICS = {
    filename: QImage(str(RHYTHM_ICONS_PATH / filename))
    for filename in os.listdir(str(RHYTHM_ICONS_PATH))
}

NOTE_TO_NOTE_CONVERSION = {
    NoteType.TAP: ("tap.png", "tape.png"),
    NoteType.LONG: ("long.png", "longe.png"),
    NoteType.FLICK: ("flick.png", "flicke.png"),
    NoteType.SLIDE: ("slide.png", "slidee.png"),
}


class ChartPicNote:
    def __init__(self, sec, note_type, lane, sync, qgroup, group_id, delta, early, late, right_flick=False):
        self.sec = sec
        self.lane = int(lane)
        self.sync = sync
        self.qgroup = qgroup
        self.group_id = group_id
        self.note_type = note_type
        self.note_pic = NOTE_PICS[NOTE_TO_NOTE_CONVERSION[note_type][0]]
        self.note_pic_smol = NOTE_PICS[NOTE_TO_NOTE_CONVERSION[note_type][1]]
        if right_flick:
            self.note_pic = self.note_pic.mirrored(horizontal=True, vertical=False)
            self.note_pic_smol = self.note_pic_smol.mirrored(horizontal=True, vertical=False)
        self.delta = int(delta)
        self.early = int(early)
        self.late = int(late)


class DraggableQScrollArea(QScrollArea):
    scroll_area: QScrollArea

    def __init__(self, *args):
        super().__init__(*args)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.original_y = self.verticalScrollBar().value()
            self.original_x = self.horizontalScrollBar().value()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        delta = event.pos() - self.drag_start_position
        if delta.manhattanLength() < QApplication.startDragDistance():
            return
        self.verticalScrollBar().setValue(self.original_y - delta.y())
        self.horizontalScrollBar().setValue(self.original_x - delta.x())


class ChartPicGenerator:

    def __init__(self, song_id, difficulty, main_window):
        self.song_id = song_id
        if isinstance(difficulty, int):
            difficulty = Difficulty(difficulty)
        self.difficulty = difficulty
        self.notes = fetch_chart(None, song_id, difficulty, event=False, skip_load_notes=False)[0]
        if self.notes is None:
            self.notes = fetch_chart(None, song_id, difficulty, event=True, skip_load_notes=False)[0]
        self.notes['finishPos'] -= 1
        self.notes_into_group()
        self.generate_note_objects()

        self.main = main_window
        self.initialize_ui()

        self.p = QPainter(self.label.pixmap())
        self.p.setRenderHint(QPainter.Antialiasing)
        self.draw()
        self.label.repaint()

    def hook_drag_move(self):
        self.label.dragEnterEvent()
        self.label.mousePressEvent()

    def set_unit(self, unit: Unit, redraw=True):
        self.unit = unit
        self.paint_skill()
        self.draw()
        if redraw:
            self.label.repaint()

    def notes_into_group(self):
        long_groups = list()
        long_stack = defaultdict(lambda: list())
        for _, note in self.notes.iterrows():
            # Handle long differently
            lane = note['finishPos']
            if note['note_type'] == NoteType.LONG and lane not in long_stack:
                long_stack[lane].append((_, note))
            elif lane in long_stack:
                long_stack[lane].append((_, note))
                long_groups.append(long_stack.pop(lane))
        long_dummy_group = 2000
        for pair in long_groups:
            group_id = max(pair[0][1]['groupId'], pair[1][1]['groupId'])
            if group_id == 0:
                group_id = long_dummy_group
                long_dummy_group += 1
            self.notes.loc[pair[0][0], 'groupId'] = group_id
            self.notes.loc[pair[1][0], 'groupId'] = group_id

    def initialize_ui(self):
        self.y_total = MAX_SECS_PER_GROUP * SEC_HEIGHT + 2 * Y_MARGIN
        self.x_total = (2 * X_MARGIN + (5 - 1) * LANE_DISTANCE) * self.n_groups + RIGHT_MARGIN

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignBottom)
        self.label.setFixedSize(self.x_total, self.y_total)

        canvas = QPixmap(self.x_total, self.y_total)
        self.label.setPixmap(canvas)

        scroll = DraggableQScrollArea()
        scroll.setWidget(self.label)
        # Scroll to bottom
        vbar = scroll.verticalScrollBar()
        vbar.setValue(vbar.maximum())
        self.main.setCentralWidget(scroll)
        self.y_max = 800
        self.x_max = min(1700, self.x_total + 20)
        self.main.setGeometry(200, 200, self.x_max, self.y_max)

    def get_x(self, lane, group):
        return X_MARGIN + lane * LANE_DISTANCE + (2 * X_MARGIN + 4 * LANE_DISTANCE) * group

    # Lanes start from 0
    def get_y(self, sec, group=None, offset_group=0):
        if group is not None:
            return self.y_total - Y_MARGIN - (sec - group * MAX_SECS_PER_GROUP) * SEC_HEIGHT
        else:
            return self.y_total - Y_MARGIN - (
                    sec - (sec // MAX_SECS_PER_GROUP + offset_group) * MAX_SECS_PER_GROUP) * SEC_HEIGHT

    def generate_note_objects(self, deltas=None, windows=None):
        # Number of groups = ceil(last sec // MAX_SECS_PER_GROUP)
        self.last_sec = int(self.notes.sec.iloc[-1]) + 1
        self.n_groups = ceil(self.last_sec / MAX_SECS_PER_GROUP)
        self.note_groups = list()
        for n in range(self.n_groups):
            group = list()
            df_slice = self.notes[(n * MAX_SECS_PER_GROUP - Y_MARGIN / SEC_HEIGHT <= self.notes['sec']) &
                                  (self.notes['sec'] <= (n + 1) * MAX_SECS_PER_GROUP + Y_MARGIN / SEC_HEIGHT)]
            for _, row in df_slice.iterrows():
                note_object = ChartPicNote(sec=row['sec'], note_type=row['note_type'], lane=row['finishPos'],
                                           sync=row['sync'], qgroup=n, group_id=row['groupId'],
                                           delta=deltas[_] if deltas is not None else 0,
                                           early=windows[_][0] if windows is not None else 0,
                                           late=windows[_][1] if windows is not None else 0,
                                           right_flick=row['status'] == 2 and row['note_type'] == NoteType.FLICK)
                group.append(note_object)
            self.note_groups.append(group)

    def draw(self):
        self.draw_grid_and_secs()
        self.draw_sync_lines()
        self.draw_group_lines()
        self.draw_notes()

    def paint_skill(self):
        for card_idx, card in enumerate(self.unit.all_cards()):
            skill = card.sk
            interval = skill.interval
            duration = skill.duration
            skill_times = int((self.last_sec - 3) // interval)
            skill_time = 1
            group = 0
            while skill_time <= skill_times:
                left = skill_time * interval
                right = skill_time * interval + duration
                #  Do not paint if skill entirely outside group
                if left > (group + 1) * MAX_SECS_PER_GROUP - Y_MARGIN / SEC_HEIGHT:
                    group += 1
                    skill_time -= 1
                    continue
                skill_brush = QBrush(QColor(*SKILL_BASE[skill.skill_type]['color'], 100))
                self.p.setPen(QPen())
                self.p.setBrush(skill_brush)
                x = self.get_x(card_idx, group)
                y = self.get_y(right, group)
                self.p.drawRect(x - SKILL_PAINT_WIDTH // 2,
                                y,
                                SKILL_PAINT_WIDTH,
                                duration * SEC_HEIGHT)
                skill_time += 1

    def draw_grid_and_secs(self):
        font = QFont()
        font.setPixelSize(36)
        self.p.setFont(font)

        vertical_grid_pen = QPen(QColor(80, 80, 80))
        vertical_grid_pen.setWidth(5)
        self.p.setPen(vertical_grid_pen)
        for group in range(self.n_groups):
            for lane in range(5):
                x = self.get_x(lane, group)
                self.p.drawLine(x, 0, x, self.y_total)

        horizontal_grid_bold_pen = QPen(QColor(120, 120, 120))
        horizontal_grid_bold_pen.setWidth(5)
        horizontal_grid_light_pen = QPen(QColor(80, 80, 80))
        horizontal_grid_light_pen.setWidth(3)
        for group in range(self.n_groups):
            for sec in range(MAX_SECS_PER_GROUP + 1):
                if sec % 5 == 0:
                    self.p.setPen(horizontal_grid_bold_pen)
                else:
                    self.p.setPen(horizontal_grid_light_pen)
                y = self.get_y(sec, group=0)
                self.p.drawLine(self.get_x(0, group), y, self.get_x(4, group), y)
                self.p.drawText(self.get_x(4, group) + 60, y, str(sec + MAX_SECS_PER_GROUP * group))

    def draw_notes(self):
        for group_idx, group in enumerate(self.note_groups):
            for note in group:
                x = self.get_x(note.lane, group_idx) - note.note_pic.width() // 2
                y = self.get_y(note.sec, group_idx) - note.note_pic.height() // 2
                self.p.drawImage(QPoint(x, y), note.note_pic)

    def _is_double_drawn_note(self, note: ChartPicNote):
        for _ in range(self.n_groups):
            if MAX_SECS_PER_GROUP * _ - Y_MARGIN / SEC_HEIGHT <= note.sec <= MAX_SECS_PER_GROUP * _ + Y_MARGIN / SEC_HEIGHT:
                return True
        return False

    def draw_sync_lines(self):
        sync_line_pen = QPen(QColor(250, 250, 240))
        sync_line_pen.setWidth(3)
        self.p.setPen(sync_line_pen)
        for group_idx, qt_group in enumerate(self.note_groups):
            sync_pairs = defaultdict(lambda: list())
            for note in qt_group:
                if note.sync == 0:
                    continue
                sync_pairs[note.sec].append(note)
            for values in sync_pairs.values():
                l = min(values[0].lane, values[1].lane)
                r = max(values[0].lane, values[1].lane)
                sec = values[0].sec
                y = self.get_y(sec, group_idx)
                self.p.drawLine(self.get_x(l, group_idx), y, self.get_x(r, group_idx), y)

    def _draw_group_line(self, note1, note2, group):
        group_line_pen = QPen(QColor(180, 180, 180))
        group_line_pen.setWidth(20)
        self.p.setPen(group_line_pen)
        x1 = self.get_x(note1['finishPos'], group)
        x2 = self.get_x(note2['finishPos'], group)
        y1 = self.get_y(note1['sec'], group)
        y2 = self.get_y(note2['sec'], group)
        self.p.drawLine(x1, y1, x2, y2)

    def draw_group_lines(self):
        for group_idx, qt_group in enumerate(self.note_groups):
            group_ids = set()
            for note in qt_group:
                if note.group_id == 0:
                    continue
                group_ids.add(note.group_id)
            grouped_notes_df = self.notes[self.notes['groupId'].isin(group_ids)]
            for group_id, grouped_notes in grouped_notes_df.groupby("groupId"):
                for l, r in zip(grouped_notes.iloc[1:].T.to_dict().values(),
                                grouped_notes.iloc[:-1].T.to_dict().values()):
                    self._draw_group_line(l, r, group_idx)

    def hook_simulation_results(self, all_cards, results):
        # TODO: Support grand chart
        all_cards = all_cards[0]
        if len(all_cards) > 6:
            return
        self.set_unit(Unit.from_list(cards=all_cards), redraw=False)

        delta_list = list()
        window_list = list()
        perfect_score_array = results[1][0]
        score_matrix = results[1][1]
        n_intervals = score_matrix.shape[1] - 1
        for i in range(len(perfect_score_array)):
            max_score = score_matrix[i, :].max()
            delta = max_score - perfect_score_array[i]
            if delta == 0:
                window_list.append((0, 0))
            else:
                temp = np.array(range(1, n_intervals + 2)) * (score_matrix[i, :] == max_score)
                temp = temp[temp != 0] - 1
                window_list.append((-200 + temp.min() * 400 / n_intervals, -200 + temp.max() * 400 / n_intervals))
            delta_list.append(delta)

        self.generate_note_objects(delta_list, window_list)
        for group_idx, qt_group in enumerate(self.note_groups):
            for note in qt_group:
                self.draw_abuse(note, group_idx)
        self.label.repaint()

    def draw_abuse(self, note: ChartPicNote, group):
        if note.delta == 0:
            return

        x_note = self.get_x(note.lane, group) - note.note_pic_smol.width() // 2
        y_early = self.get_y(note.sec + note.early / 1000, group)
        shifted_y_early = y_early - note.note_pic_smol.height() // 2
        y_late = self.get_y(note.sec + note.late / 1000, group)
        shifted_y_late = y_late - note.note_pic_smol.height() // 2
        self.p.drawImage(QPoint(x_note, shifted_y_early), note.note_pic_smol)
        self.p.drawImage(QPoint(x_note, shifted_y_late), note.note_pic_smol)
        lane0 = self.get_x(0, group)
        lane4 = self.get_x(4, group)
        self.p.setPen(QPen(Qt.green))
        self.p.drawLine(lane0, y_early, lane4, y_early)
        self.p.setPen(QPen(Qt.red))
        self.p.drawLine(lane0, y_late, lane4, y_late)

        x = self.get_x(note.lane, group) - note.note_pic.width() // 2
        y = self.get_y(note.sec, group) + note.note_pic.height()
        font = QFont()
        font.setBold(True)
        font.setPixelSize(30)
        pen = QPen()
        pen.setWidth(1)
        pen.setColor(Qt.white)
        brush = QBrush(Qt.black)
        path = QPainterPath()
        path.addText(x, y, font, str(note.delta))
        self.p.setFont(font)
        self.p.setPen(pen)
        self.p.setBrush(brush)
        self.p.drawPath(path)
        font.setPixelSize(24)
        path = QPainterPath()
        path.addText(x, y + 40, font, "{} {}".format(note.early, note.late))
        self.p.drawPath(path)

    def save_image(self):
        self.label.pixmap().save("{}-{}.png".format(self.song_id, self.difficulty))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("Bruh")
    main_window = QMainWindow()
    main_window.show()
    unit = Unit.from_query("sae4 arisu3 riina5 riina5u hajime4 yui2")
    live = Live()
    live.set_music(score_id=55, difficulty=Difficulty.MPLUS)
    live.set_unit(unit)
    sim = Simulator(live)
    cpg = ChartPicGenerator(55, Difficulty(5), main_window)
    cpg.set_unit(unit)
    app.exec_()
