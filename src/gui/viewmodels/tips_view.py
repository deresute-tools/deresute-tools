from PyQt5.QtWidgets import QLabel

from gui.events.service.tips_refresher_service import start_tip_refresher_service
from gui.events.state_change_events import SetTipTextEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe


class TipView(QLabel):
    def __init__(self):
        super().__init__()
        eventbus.eventbus.register(self)
        start_tip_refresher_service()

    @subscribe(SetTipTextEvent)
    def set_text(self, event):
        self.setText(event.text)
