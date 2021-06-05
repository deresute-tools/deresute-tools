from PyQt5.QtWidgets import QTableWidget, QAbstractItemView

from exceptions import InvalidUnit
from gui.events.calculator_view_events import SetSupportCardsEvent, RequestSupportTeamEvent, SupportTeamSetMusicEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.events.value_accessor_events import GetCustomPotsEvent, GetCustomBonusEvent, GetGrooveSongColor
from gui.viewmodels.simulator.calculator import CardsWithUnitUuidAndExtraData
from gui.viewmodels.utils import NumericalTableWidgetItem, ImageWidget
from logic.grandlive import GrandLive
from logic.grandunit import GrandUnit
from logic.live import Live
from logic.unit import Unit
from settings import IMAGE_PATH64


class SupportView:
    def __init__(self, main):
        self.widget = QTableWidget(main)
        self.widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.widget.setSortingEnabled(True)
        self.widget.verticalHeader().setVisible(False)
        self.widget.setRowCount(10)
        self.widget.setColumnCount(5)
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.horizontalHeader().setSectionResizeMode(1)  # Not allow change icon column size
        self.widget.setHorizontalHeaderLabels(["", "Vocal", "Dance", "Visual", "Total"])
        self.widget.verticalHeader().setDefaultSectionSize(72)

    def set_model(self, model):
        self.model = model

    def display_support(self, support):
        support[:, [2, 3]] = support[:, [3, 2]]
        for r in range(len(support)):
            card_id = support[r][0]
            image = ImageWidget(str(IMAGE_PATH64 / "{:06d}.jpg".format(card_id)), self.widget)
            self.widget.setCellWidget(r, 0, image)
            for c in range(1, 5):
                self.widget.setItem(r, c, NumericalTableWidgetItem(support[r][c]))


class SupportModel:
    extended_cards_data: CardsWithUnitUuidAndExtraData

    def __init__(self, view):
        self.view = view
        self.live = Live()
        self.music = None
        self.card_ids = None
        self.cards = list()
        self.extended_cards_data = None
        eventbus.eventbus.register(self)

    @subscribe(SetSupportCardsEvent)
    def set_cards(self, event: SetSupportCardsEvent):
        self.extended_cards_data = event.extended_cards_data
        self.cards = self.extended_cards_data.cards
        try:
            if self.extended_cards_data.lock_unit:
                custom_pots = None
            else:
                custom_pots = eventbus.eventbus.post_and_get_first(GetCustomPotsEvent())
            if len(self.cards) == 15:
                unit = GrandUnit.from_list(self.cards, custom_pots)
                self.live = GrandLive()
                self.live.set_unit(unit)
            else:
                unit = Unit.from_list(self.cards, custom_pots)
                self.live = Live()
                self.live.set_unit(unit)
        except InvalidUnit:
            return False
        return True

    @subscribe(SupportTeamSetMusicEvent)
    def set_music(self, event):
        score_id = event.score_id
        difficulty = event.difficulty
        self.live.set_music(score_id=score_id, difficulty=difficulty, skip_load_notes=True)
        self.music = (score_id, difficulty)

    @subscribe(RequestSupportTeamEvent)
    def generate_support(self, event):
        if self.live.unit is None:
            return
        if self.extended_cards_data.lock_chart and self.extended_cards_data is not None and self.extended_cards_data.score_id is not None:
            self.live.set_music(score_id=self.extended_cards_data.score_id, difficulty=self.extended_cards_data.diff_id)
        else:
            if self.music is not None:
                self.live.set_music(score_id=self.music[0], difficulty=self.music[1])
        if self.extended_cards_data.lock_chart and self.extended_cards_data.groove_song_color is not None:
            groove_song_color = self.extended_cards_data.groove_song_color
        else:
            groove_song_color = eventbus.eventbus.post_and_get_first(GetGrooveSongColor())

        if groove_song_color is not None:
            self.live.color = groove_song_color
        if self.extended_cards_data.lock_unit:
            self.live.set_extra_bonus(
                self.extended_cards_data.extra_bonus,
                self.extended_cards_data.special_option,
                self.extended_cards_data.special_value)
        else:
            self.live.set_extra_bonus(*eventbus.eventbus.post_and_get_first(GetCustomBonusEvent()))
        self.live.get_support()
        self.view.display_support(self.live.support.copy())
        return self.live.get_appeals(), self.live.get_support(), self.live.get_life()
