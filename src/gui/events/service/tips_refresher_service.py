import random
from time import sleep, time

from PyQt5.QtCore import QRunnable, pyqtSlot

from gui.events.state_change_events import SetTipTextEvent, InjectTextEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from gui.events.utils.threadpool import threadpool

DELAY_SECS = 20


class TipRefresherService(QRunnable):
    TIPS = {
        "Tip: You can use Ctrl/Alt + 1/2/3/... in the quicksearch bar to quickly send cards to the simulator.",
        "Tip: Select a unit then press Ctrl + D or Ctrl + Shift + D to clone it.",
        "Tip: Something might happen if you run autoplay simulations at 346ms offset without using autoplay mode.",
        "Tip: Importing cards from game ID uses SSR posters to detect what cards you have.",
        "Tip: Use the \"Partial match\" option.",
        "Tip: Double clicking a song will also popup the chart viewer.",
        "Tip: Right clicking the song list will toggle between note type count and note type percentage.",
        "Tip: Leftmost red square = Center, rightmost blue square = Guest.",
    }

    def __init__(self):
        super().__init__()
        self.current_tip = None
        self.scheduled_time = time()
        self.running = True
        eventbus.eventbus.register(self)

    @pyqtSlot()
    def run(self):
        self.schedule_tip_display()

    def schedule_tip_display(self):
        while self.running:
            current = time()
            if current >= self.scheduled_time:
                self.select_next_tip()
                self.send_to_view()
                self.set_timer(DELAY_SECS)
            else:
                sleep(self.scheduled_time - current)

    def select_next_tip(self):
        while True:
            next_tip = random.sample(self.TIPS, 1)[0]
            if self.current_tip != next_tip:
                self.current_tip = next_tip
                return

    def send_to_view(self):
        eventbus.eventbus.post(SetTipTextEvent(self.current_tip))

    def set_timer(self, offset):
        self.scheduled_time = time() + offset

    def disable(self):
        self.running = False

    @subscribe(InjectTextEvent)
    def inject_message(self, event):
        self.set_timer(event.offset)
        eventbus.eventbus.post(SetTipTextEvent(event.text))


__service = TipRefresherService()


def start_tip_refresher_service():
    threadpool.start(__service)


def kill_tip_refresher_service():
    __service.disable()
