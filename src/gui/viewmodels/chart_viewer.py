from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QApplication

from chart_pic_generator import BaseChartPicGenerator
from gui.events.chart_viewer_events import SendMusicEvent, HookAbuseToChartViewerEvent, HookUnitToChartViewerEvent, \
    ToggleMirrorEvent, PopupChartViewerEvent
from gui.events.song_view_events import GetSongDetailsEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.events.value_accessor_events import GetMirrorFlagEvent


class ChartViewerListener:
    def __init__(self):
        self.chart_viewer = None
        eventbus.eventbus.register(self)

    @subscribe(PopupChartViewerEvent)
    def popup_chart_viewer(self, event=None):
        if self.chart_viewer is None:
            self.chart_viewer = ChartViewer(self)
        if event.look_for_chart:
            score_id, diff_id, _, _, _ = eventbus.eventbus.post_and_get_first(GetSongDetailsEvent())
            eventbus.eventbus.post(SendMusicEvent(score_id, diff_id))


class ChartViewer(QMainWindow):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.generator = None
        eventbus.eventbus.register(self)
        self.setGeometry(200, 200, 1700, 800)
        self.setWindowTitle("Chart Viewer")
        self.show()

    @subscribe(SendMusicEvent)
    def hook_music(self, event: SendMusicEvent):
        mirror_flag = eventbus.eventbus.post_and_get_first(GetMirrorFlagEvent())
        self.generator = BaseChartPicGenerator.get_generator(event.song_id, event.difficulty, self, reset_main=False,
                                                             mirrored=mirror_flag)

    @subscribe(HookAbuseToChartViewerEvent)
    def hook_abuse(self, event: HookAbuseToChartViewerEvent):
        if self.generator is None:
            return
        self.generator.hook_abuse(event.cards, event.abuse_df)

    @subscribe(HookUnitToChartViewerEvent)
    def hook_unit(self, event: HookUnitToChartViewerEvent):
        if self.generator is None:
            return
        self.generator.hook_cards(event.cards)

    @subscribe(ToggleMirrorEvent)
    def toggle_mirror(self, event: ToggleMirrorEvent):
        if self.generator is None:
            return
        self.generator = self.generator.mirror_generator(event.mirrored)

    def keyPressEvent(self, event):
        key = event.key()
        if QApplication.keyboardModifiers() == Qt.ControlModifier and key == Qt.Key_S:
            self.generator.save_image()

    def closeEvent(self, *args, **kwargs):
        eventbus.eventbus.unregister(self)
        self.generator = None
        self.parent.chart_viewer = None
        super().closeEvent(*args, **kwargs)


listener = ChartViewerListener()
