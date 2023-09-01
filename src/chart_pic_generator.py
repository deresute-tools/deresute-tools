import os
import sys
from abc import abstractmethod, ABC
from collections import defaultdict
from math import ceil

from PyQt5.QtCore import Qt, QPoint, QRectF, QRect
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QFont, QBrush, QPainterPath, qRgba, QPolygonF
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QScrollArea

from exceptions import InvalidUnit
from logic.grandunit import GrandUnit
from logic.live import fetch_chart, Live
from logic.unit import Unit
from settings import RHYTHM_ICONS_PATH, CHART_PICS_PATH
from simulator import Simulator, SimulationResult
from statemachine import AbuseData
from static.judgement import Judgement
from static.note_type import NoteType
from static.skill import SKILL_BASE
from static.song_difficulty import Difficulty
from utils import storage

_QFont = QFont


def QFont():
    qf = _QFont('Sans Serif')
    qf.setStyleHint(_QFont.SansSerif)
    return qf


SEC_HEIGHT = 500
X_MARGIN = 100
Y_MARGIN = 70
RIGHT_MARGIN = 0
LEFT_MARGIN = 50
MAX_Y = 5000
MAX_SECS_PER_GROUP = (MAX_Y - Y_MARGIN * 2) // SEC_HEIGHT

LANE_DISTANCE = 70
SKILL_PAINT_WIDTH = 60

LANE_DISTANCE_GRAND = 25
SKILL_PAINT_WIDTH_GRAND = 22

WINDOW_HEIGHT = 800
MAX_WINDOW_WIDTH = 1700

NOTE_PICS = {
    filename: QImage(str(RHYTHM_ICONS_PATH / filename))
    for filename in os.listdir(str(RHYTHM_ICONS_PATH))
}

CACHED_GRAND_NOTE_PICS = dict()


class ChartPicNote:
    def __init__(self, sec, note_type, lane, sync, qgroup, group_id, delta, early, late, right_flick=False,
                 grand=False, span=0, great=False):
        self.sec = sec
        self.lane = int(lane)
        self.sync = sync
        self.qgroup = qgroup
        self.group_id = group_id
        self.note_type = note_type
        self.right_flick = right_flick
        self.grand = grand
        self.span = span
        self.great = great

        self.get_note_pic()

        self.delta = int(delta)
        self.early = int(early)
        self.late = int(late)

    def get_note_pic(self):
        if self.note_type == NoteType.TAP:
            note_file_prefix = "tap"
        elif self.note_type == NoteType.LONG:
            note_file_prefix = "long"
        elif self.note_type == NoteType.SLIDE:
            note_file_prefix = "slide"
        elif self.note_type == NoteType.FLICK and self.right_flick:
            note_file_prefix = "flickr"
        elif self.note_type == NoteType.FLICK and not self.right_flick:
            note_file_prefix = "flickl"
        else:
            note_file_prefix = "damage"
        if self.grand:
            note_file_prefix = "g" + note_file_prefix
            self.note_pic = ChartPicNote.get_grand_note(note_file_prefix, self.span, False)
            self.note_pic_smol = ChartPicNote.get_grand_note(note_file_prefix + "e", self.span, True)
        else:
            self.note_pic = NOTE_PICS["{}.png".format(note_file_prefix)]
            self.note_pic_smol = NOTE_PICS["{}e.png".format(note_file_prefix)]

    @classmethod
    def get_grand_note(cls, note_file_prefix, span, tiny=False):
        if note_file_prefix in CACHED_GRAND_NOTE_PICS and span in CACHED_GRAND_NOTE_PICS[note_file_prefix]:
            return CACHED_GRAND_NOTE_PICS[note_file_prefix][span]
        if note_file_prefix not in CACHED_GRAND_NOTE_PICS:
            CACHED_GRAND_NOTE_PICS[note_file_prefix] = dict()

        CACHED_GRAND_NOTE_PICS[note_file_prefix][span] = ChartPicNote.generate_grand_note(note_file_prefix, span, tiny)
        return CACHED_GRAND_NOTE_PICS[note_file_prefix][span]

    @classmethod
    def generate_grand_note(cls, note_file_prefix, span, tiny=False):
        l = NOTE_PICS["{}1.png".format(note_file_prefix)]
        m = NOTE_PICS["{}2.png".format(note_file_prefix)]
        r = NOTE_PICS["{}3.png".format(note_file_prefix)]
        w = span * LANE_DISTANCE_GRAND
        if tiny:
            w = w * 0.75
        res = QImage(int(l.width()
                         + r.width()
                         + w),
                     int(l.height()),
                     QImage.Format_ARGB32)
        res.fill(qRgba(0, 0, 0, 0))
        painter = QPainter(res)
        painter.drawImage(QPoint(0, 0), l)
        painter.drawImage(QRectF(l.width(), 0, w, m.height()), m, QRectF(0, 0, m.width(), m.height()))
        painter.drawImage(QPoint(int(l.width() + w), 0), r)
        return res


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
        self.verticalScrollBar().setValue(int(self.original_y - delta.y() * 1.5))
        self.horizontalScrollBar().setValue(int(self.original_x - delta.x() * 1.5))


class BaseChartPicGenerator(ABC):
    LANE_DISTANCE = LANE_DISTANCE
    SKILL_PAINT_WIDTH = SKILL_PAINT_WIDTH

    unit = None

    def __init__(self, song_id, difficulty, main_window, grand, reset_main=True, mirrored=False):
        self.song_id = song_id
        self.difficulty = difficulty
        self.main = main_window
        self.grand = grand
        if grand:
            self.lane_count = 15
        else:
            self.lane_count = 5

        self.notes = fetch_chart(None, song_id, difficulty, event=False, skip_load_notes=False)[0]
        if self.notes is None:
            self.notes = fetch_chart(None, song_id, difficulty, event=True, skip_load_notes=False)[0]
        self.notes['finishPos'] -= 1
        self.mirrored = mirrored
        if mirrored:
            if not grand:
                self.notes['finishPos'] = 4 - self.notes['finishPos']
            else:
                self.notes['finishPos'] = 15 - (self.notes['finishPos'] + self.notes['status'])
        self.notes_into_group()
        self.generate_note_objects()

        self.initialize_ui()
        if reset_main:
            self.main.setGeometry(200, 200, self.x_max, self.y_max)

        self.p = QPainter(self.label.pixmap())
        self.p.setRenderHint(QPainter.Antialiasing)
        self.draw()
        self.label.repaint()

    def mirror_generator(self, mirrored):
        if self.mirrored == mirrored:
            return self
        return BaseChartPicGenerator.get_generator(self.song_id, self.difficulty, self.main, reset_main=False,
                                                   mirrored=mirrored)

    @classmethod
    def get_generator(cls, song_id, difficulty, main_window, reset_main=True, mirrored=False):
        if isinstance(difficulty, int):
            difficulty = Difficulty(difficulty)
        if difficulty == Difficulty.PIANO or difficulty == Difficulty.FORTE:
            return GrandChartPicGenerator(song_id, difficulty, main_window, True, reset_main, mirrored)
        else:
            return BasicChartPicGenerator(song_id, difficulty, main_window, False, reset_main, mirrored)

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
        self.x_total = LEFT_MARGIN + (
                2 * X_MARGIN + (self.lane_count - 1) * self.LANE_DISTANCE) * self.n_groups + RIGHT_MARGIN

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
        self.y_max = WINDOW_HEIGHT
        self.x_max = min(MAX_WINDOW_WIDTH, self.x_total + 20)

    def get_x(self, lane, group):
        return int(LEFT_MARGIN + X_MARGIN + lane * self.LANE_DISTANCE + (
                2 * X_MARGIN + (self.lane_count - 1) * self.LANE_DISTANCE) * group)

    def get_y(self, sec, group=None, offset_group=0):
        if group is not None:
            return int(self.y_total - Y_MARGIN - (sec - group * MAX_SECS_PER_GROUP) * SEC_HEIGHT)
        else:
            return int(self.y_total - Y_MARGIN - (
                    sec - (sec // MAX_SECS_PER_GROUP + offset_group) * MAX_SECS_PER_GROUP) * SEC_HEIGHT)

    # Lanes start from 0
    def generate_note_objects(self, abuse_data: AbuseData = None):
        # Number of groups = ceil(last sec // MAX_SECS_PER_GROUP)
        self.last_sec_float = self.notes.sec.iloc[-1]
        self.last_sec = int(self.last_sec_float) + 1
        self.n_groups = ceil(self.last_sec / MAX_SECS_PER_GROUP)
        self.note_groups = list()
        for n in range(self.n_groups):
            group = list()
            df_slice = self.notes[(n * MAX_SECS_PER_GROUP - Y_MARGIN / SEC_HEIGHT <= self.notes['sec']) &
                                  (self.notes['sec'] <= (n + 1) * MAX_SECS_PER_GROUP + Y_MARGIN / SEC_HEIGHT)]
            for _, row in df_slice.iterrows():
                right_flick = row['note_type'] == NoteType.FLICK and (row['status'] == 2 and not self.grand) or (
                        row['type'] == 7 and self.grand)
                if self.mirrored:
                    right_flick = not right_flick
                if abuse_data is not None and abuse_data.score_delta[_] > 0:
                    delta = abuse_data.score_delta[_]
                    early = abuse_data.window_l[_] // 1E3
                    late = abuse_data.window_r[_] // 1E3
                    great = abuse_data.judgements[_] is Judgement.GREAT
                else:
                    delta = 0
                    early = 0
                    late = 0
                    great = False
                note_object = ChartPicNote(sec=row['sec'], note_type=row['note_type'], lane=row['finishPos'],
                                           sync=row['sync'], qgroup=n, group_id=row['groupId'],
                                           delta=delta, early=early, late=late, right_flick=right_flick,
                                           grand=self.grand, span=row['status'] - 1 if self.grand else 0,
                                           great=great)
                group.append(note_object)
            self.note_groups.append(group)

    def draw(self):
        self.draw_grid_and_secs()
        self.draw_sync_lines()
        self.draw_group_lines()
        self.draw_notes()

    def hook_cards(self, all_cards, redraw=True):
        try:
            if len(all_cards) == 15:
                unit = GrandUnit.from_list(all_cards)
            else:
                unit = Unit.from_list(cards=all_cards[:5])
        except InvalidUnit:
            return
        # Skip drawing if same unit else reset drawing
        if not self.grand and isinstance(unit, GrandUnit):
            unit = unit.ua
        if unit == self.unit:
            return
        self.p.fillRect(0, 0, self.x_total, self.y_total, Qt.black)
        self.unit = unit
        self.paint_skill()
        self.draw()
        if redraw:
            self.label.repaint()

    def paint_skill(self):
        for card_idx, card in enumerate(self.unit.all_cards()):
            skill = card.sk
            interval = skill.interval
            duration = skill.duration
            skill_times = int((self.last_sec_float - 3) // interval)
            skill_time = 1
            group = 0
            while group < self.n_groups:
                left = skill_time * interval
                right = skill_time * interval + duration
                #  Do not paint if skill entirely outside group
                if left > (group + 1) * MAX_SECS_PER_GROUP + Y_MARGIN / SEC_HEIGHT:
                    group += 1
                    skill_time -= 1
                    continue
                if self.grand and (skill_time - 1) % 3 != skill.offset:
                    skill_time += 1
                    continue
                if skill_time > skill_times:
                    break
                if skill.skill_type is None:
                    skill_time += 1
                    continue
                skill_brush = QBrush(QColor(*SKILL_BASE[skill.skill_type]['color'], 100))
                self.p.setPen(QPen())
                self.p.setBrush(skill_brush)
                # Need to convert grand lane
                draw_card_idx = card_idx
                if self.grand:
                    if card_idx < 5:
                        draw_card_idx += 5
                    elif 5 <= card_idx < 10:
                        draw_card_idx -= 5
                x = self.get_x(draw_card_idx, group)
                y = self.get_y(right, group)
                self.p.drawRect(int(x - self.SKILL_PAINT_WIDTH // 2),
                                int(y),
                                self.SKILL_PAINT_WIDTH,
                                int(duration * SEC_HEIGHT))
                skill_time += 1

    def draw_grid_and_secs(self):
        font = QFont()
        font.setPixelSize(36)
        self.p.setFont(font)

        vertical_grid_pen = QPen(QColor(80, 80, 80))
        vertical_grid_pen.setWidth(5)
        self.p.setPen(vertical_grid_pen)
        for group in range(self.n_groups):
            for lane in range(self.lane_count):
                x = self.get_x(lane, group)
                self.p.drawLine(x, 0, x, self.y_total)

        horizontal_grid_bold_pen = QPen(QColor(120, 120, 120))
        horizontal_grid_bold_pen.setWidth(5)
        horizontal_grid_light_pen = QPen(QColor(80, 80, 80))
        horizontal_grid_light_pen.setWidth(3)
        for group in range(self.n_groups):
            for sec in range(MAX_SECS_PER_GROUP + 1):
                if (sec + group * MAX_SECS_PER_GROUP) % 5 == 0:
                    self.p.setPen(horizontal_grid_bold_pen)
                else:
                    self.p.setPen(horizontal_grid_light_pen)
                y = self.get_y(sec, group=0)
                self.p.drawLine(self.get_x(0, group), y, self.get_x(self.lane_count - 1, group), y)
                tm = sec + MAX_SECS_PER_GROUP * group
                self.p.drawText(QRect(self.get_x(0, group) - 111, y - 25, 70, 100), Qt.AlignRight,
                                "{}:{:0>2}\n{}".format(tm // 60, tm % 60, self.notes[self.notes['sec'] <= tm].shape[0]))

    @abstractmethod
    def draw_notes(self):
        pass

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
                # Skip in case of sync == 1 but only 1 value because this game has dumb codes
                if len(values) != 2:
                    continue
                l = min(values[0].lane, values[1].lane)
                r = max(values[0].lane, values[1].lane)
                sec = values[0].sec
                y = self.get_y(sec, group_idx)
                self.p.drawLine(self.get_x(l, group_idx), y, self.get_x(r, group_idx), y)

    @abstractmethod
    def _draw_group_line(self, note1, note2, group):
        pass

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

    def hook_abuse(self, all_cards, abuse_data):
        self.hook_cards(all_cards, False)

        self.generate_note_objects(abuse_data)
        for group_idx, qt_group in enumerate(self.note_groups):
            for note in qt_group:
                self.draw_abuse(note, group_idx)
        self.label.repaint()

    def draw_abuse(self, note: ChartPicNote, group):
        if note.delta == 0:
            return

        x_note = self.get_x(note.lane + note.span / 2, group) - note.note_pic_smol.width() // 2
        y_early = self.get_y(note.sec + note.early / 1000, group)
        shifted_y_early = y_early - note.note_pic_smol.height() // 2
        y_late = self.get_y(note.sec + note.late / 1000, group)
        shifted_y_late = y_late - note.note_pic_smol.height() // 2
        self.p.drawImage(QPoint(x_note, shifted_y_early), note.note_pic_smol)
        self.p.drawImage(QPoint(x_note, shifted_y_late), note.note_pic_smol)
        lane_l = self.get_x(0, group)
        lane_r = self.get_x(self.lane_count - 1, group)
        self.p.setPen(QPen(Qt.green))
        self.p.drawLine(lane_l, y_early, lane_r, y_early)
        self.p.setPen(QPen(Qt.red))
        self.p.drawLine(lane_l, y_late, lane_r, y_late)

        x = self.get_x(note.lane + note.span / 2, group) - note.note_pic.width() // 2
        y = self.get_y(note.sec, group) + note.note_pic.height()
        font = QFont()
        font.setBold(True)
        font.setPixelSize(30)
        pen = QPen()
        pen.setWidth(1)
        pen.setColor(Qt.white)
        if note.great:
            brush = QBrush(QColor(66, 13, 110))
        else:
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
        path = CHART_PICS_PATH / "{}-{}.png".format(self.song_id, self.difficulty)
        storage.exists(path)
        self.label.pixmap().save(str(path))


class BasicChartPicGenerator(BaseChartPicGenerator):
    def _draw_group_line(self, note1, note2, group):
        group_line_pen = QPen(QColor(180, 180, 180))
        group_line_pen.setWidth(20)
        self.p.setPen(group_line_pen)
        x1 = self.get_x(note1['finishPos'], group)
        x2 = self.get_x(note2['finishPos'], group)
        y1 = self.get_y(note1['sec'], group)
        y2 = self.get_y(note2['sec'], group)
        self.p.drawLine(x1, y1, x2, y2)

    def draw_notes(self):
        for group_idx, group in enumerate(self.note_groups):
            for note in group:
                x = self.get_x(note.lane, group_idx) - note.note_pic.width() // 2
                y = self.get_y(note.sec, group_idx) - note.note_pic.height() // 2
                self.p.drawImage(QPoint(x, y), note.note_pic)


class GrandChartPicGenerator(BaseChartPicGenerator):
    LANE_DISTANCE = LANE_DISTANCE_GRAND
    SKILL_PAINT_WIDTH = SKILL_PAINT_WIDTH_GRAND

    def _draw_group_line(self, note1, note2, group):
        group_line_pen = QPen(QColor(0, 0, 0, 0))
        group_line_pen.setWidth(0)
        self.p.setPen(group_line_pen)
        group_line_brush = QBrush(QColor(180, 180, 180, 150))
        self.p.setBrush(group_line_brush)
        polygon = QPolygonF()
        x1l = self.get_x(note1['finishPos'], group)
        x1r = self.get_x(note1['finishPos'] + note1['status'] - 1, group)
        x2l = self.get_x(note2['finishPos'], group)
        x2r = self.get_x(note2['finishPos'] + note2['status'] - 1, group)
        y1 = self.get_y(note1['sec'], group)
        y2 = self.get_y(note2['sec'], group)
        polygon.append(QPoint(x1l, y1))
        polygon.append(QPoint(x1r, y1))
        polygon.append(QPoint(x2r, y2))
        polygon.append(QPoint(x2l, y2))
        self.p.drawConvexPolygon(polygon)

    def draw_notes(self):
        for group_idx, group in enumerate(self.note_groups):
            for note in group:
                x = self.get_x(note.lane + note.span / 2, group_idx) - note.note_pic.width() // 2
                y = self.get_y(note.sec, group_idx) - note.note_pic.height() // 2
                self.p.drawImage(QPoint(x, y), note.note_pic)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("Bruh")
    main_window = QMainWindow()
    main_window.show()
    unit = Unit.from_list([100936, 100708, 100914, 100584, 100456, 100964])
    live = Live()
    live.set_music(score_id=19, difficulty=4)
    live.set_unit(unit)
    sim = Simulator(live)
    # res: SimulationResult = sim.simulate(perfect_play=True, abuse=True)
    cpg = BaseChartPicGenerator.get_generator(637, Difficulty(5), main_window, mirrored=True)
    cpg.hook_cards(unit.all_cards())
    # cpg.hook_abuse(unit.all_cards(), res.abuse_data)
    app.exec_()
