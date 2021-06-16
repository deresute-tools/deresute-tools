from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QCheckBox, QLineEdit, QApplication

import customlogger as logger
from gui.events.quicksearch_events import PushCardIndexEvent, ToggleQuickSearchOptionEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from logic.search import search_engine


class ShortcutQuickSearchWidget(QLineEdit):
    def __init__(self, parent, *__args):
        super().__init__(parent, *__args)

    def keyPressEvent(self, event):
        key = event.key()
        match_dict = {
            Qt.Key_1: 0,
            Qt.Key_2: 1,
            Qt.Key_3: 2,
            Qt.Key_4: 3,
            Qt.Key_5: 4,
            Qt.Key_6: 5,
            Qt.Key_7: 6,
            Qt.Key_8: 7,
            Qt.Key_9: 8,
            Qt.Key_0: 9
        }
        if QApplication.keyboardModifiers() == Qt.AltModifier and key in match_dict:
            eventbus.eventbus.post(PushCardIndexEvent(match_dict[key], False))
            return
        if QApplication.keyboardModifiers() == Qt.ControlModifier and key in match_dict:
            eventbus.eventbus.post(PushCardIndexEvent(match_dict[key], True))
            return
        if QApplication.keyboardModifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and key == Qt.Key_Q:
            eventbus.eventbus.post(ToggleQuickSearchOptionEvent("ssr"))
            return
        if QApplication.keyboardModifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and key == Qt.Key_W:
            eventbus.eventbus.post(ToggleQuickSearchOptionEvent("idolized"))
            return
        if QApplication.keyboardModifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and key == Qt.Key_E:
            eventbus.eventbus.post(ToggleQuickSearchOptionEvent("owned_only"))
            return
        if QApplication.keyboardModifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and key == Qt.Key_R:
            eventbus.eventbus.post(ToggleQuickSearchOptionEvent("partial_match"))
            return
        super().keyPressEvent(event)


class QuickSearchView:
    def __init__(self, main):
        self.widget = ShortcutQuickSearchWidget(main)
        self.widget.setPlaceholderText("Search for card")
        self.widget.setMaximumSize(QSize(2000, 25))
        self.model = None

    def set_model(self, model):
        assert isinstance(model, QuickSearchModel)
        self.model = model
        self.widget.textChanged.connect(lambda: self.trigger())

    def trigger(self):
        self.model.call_searchengine(self.widget.text().strip())

    def focus(self):
        self.widget.setFocus()


class QuickSearchModel:
    def __init__(self, view, card_view):
        self.view = view
        self._card_view = card_view
        self.options = dict()
        eventbus.eventbus.register(self)

    def call_searchengine(self, query):
        if query == "" \
                and not self.options["ssr"].isChecked() \
                and not self.options["idolized"].isChecked() \
                and not self.options["owned_only"].isChecked():
            query = "*"
        card_ids = search_engine.advanced_single_query(
            query,
            ssr=self.options["ssr"].isChecked(),
            idolized=self.options["idolized"].isChecked(),
            partial_match=self.options["partial_match"].isChecked(),
            owned_only=self.options["owned_only"].isChecked()
        )
        logger.debug("Query: {}".format(query))
        logger.debug("Result: {}".format(card_ids))
        self._card_view.show_only_ids(card_ids)

    def _add_option(self, option, option_text, parent_layout, main):
        check_box = QCheckBox(main)
        check_box.setText(option_text)
        trigger = lambda: self.call_searchengine(self.view.widget.text().strip())
        check_box.stateChanged.connect(trigger)
        self.options[option] = check_box
        parent_layout.addWidget(check_box)

    def add_options(self, parent_layout, main):
        for option, option_text in zip(
                ["ssr", "idolized", "owned_only", "partial_match"],
                ["SSR only", "Idolized only", "Owned cards only", "Partial match"]):
            self._add_option(option, option_text, parent_layout, main)
        self.options['ssr'].setToolTip("Only show SSR and SSR+.")
        self.options['idolized'].setToolTip("Only show N+, R+, SR+, and SSR+.")
        self.options['owned_only'].setToolTip("Hide all cards you don't have.")
        self.options['partial_match'].setToolTip("This option might significantly increase query time!")
        self.options['partial_match'].setChecked(True)

    @subscribe(ToggleQuickSearchOptionEvent)
    def toggle_option(self, event: ToggleQuickSearchOptionEvent):
        self.options[event.option].nextCheckState()


class SongShortcutQuickSearchWidget(ShortcutQuickSearchWidget):
    def keyPressEvent(self, event):
        super(ShortcutQuickSearchWidget, self).keyPressEvent(event)


class SongQuickSearchView:
    def __init__(self, main):
        self.widget = SongShortcutQuickSearchWidget(main)
        self.widget.setMaximumSize(QSize(2000, 25))
        self.widget.setPlaceholderText("Search for song")
        self.model = None

    def set_model(self, model):
        assert isinstance(model, SongQuickSearchModel)
        self.model = model
        self.widget.textChanged.connect(lambda: self.trigger())

    def trigger(self):
        self.model.call_searchengine(self.widget.text().strip())

    def focus(self):
        self.widget.setFocus()


class SongQuickSearchModel:
    def __init__(self, view, song_view):
        self.view = view
        self._song_view = song_view

    def call_searchengine(self, query):
        if query == "":
            live_detail_ids = search_engine.song_query("*")
        else:
            live_detail_ids = search_engine.song_query(query)
        logger.debug("Query: {}".format(query))
        logger.debug("Result: {}".format(live_detail_ids))
        self._song_view.show_only_ids(live_detail_ids)
