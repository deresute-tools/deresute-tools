from PyQt5.QtCore import QRunnable, pyqtSlot

from gui.events.utils.threadpool import threadpool


class MyRunnable(QRunnable):
    def __init__(self, subscriber, registrant, posted_event):
        super().__init__()
        self.subscriber = subscriber
        self.registrant = registrant
        self.posted_event = posted_event

    @pyqtSlot()
    def run(self):
        self.subscriber(self.registrant, self.posted_event)


class AsyncEventBus:
    _registrants = list()
    _subscribers = dict()

    # Singleton it
    def __init__(self):
        pass

    def post(self, posted_event, high_priority=False, asynchronous=False):
        subscribed = {key: value for (key, value) in self._subscribers.items() if value == posted_event.__class__}
        for subscriber in subscribed:
            registrants = filter(lambda r: subscriber.__name__ in dir(r), self._registrants)
            registrants = list(registrants)
            for registrant in registrants:
                # Just outright drop it if full and not high priority
                if asynchronous:
                    if high_priority:
                        threadpool.start(MyRunnable(subscriber, registrant, posted_event))
                    else:
                        threadpool.tryStart(MyRunnable(subscriber, registrant, posted_event))
                else:
                    subscriber(registrant, posted_event)

    # Only synchronous, for small operations
    def post_and_get_first(self, posted_event):
        subscribed = {key: value for (key, value) in self._subscribers.items() if value == posted_event.__class__}
        for subscriber in subscribed:
            registrants = filter(lambda r: subscriber.__name__ in dir(r), self._registrants)
            for registrant in registrants:
                return subscriber(registrant, posted_event)

    def register(self, registrant):
        self._registrants.append(registrant)

    def unregister(self, registrant):
        try:
            self._registrants.remove(registrant)
        except ValueError:
            pass

    def subscribe(self, subscriber, event):
        self._subscribers[subscriber] = event


eventbus = AsyncEventBus()


def subscribe(*args, **kwargs):
    def inner(func):
        event = kwargs['event'] if args[0] is None else args[0]
        eventbus.subscribe(func, event)
        return func

    return inner
