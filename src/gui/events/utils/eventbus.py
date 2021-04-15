from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSlot

threadpool = QThreadPool()
threadpool.setMaxThreadCount(2)


class MyRunnable(QRunnable):
    def __init__(self, func):
        super().__init__()
        self.func = func

    @pyqtSlot()
    def run(self):
        self.func()


class AsyncEventBus:
    _registrants = list()
    _subscribers = dict()

    # Singleton it
    def __init__(self):
        pass

    def post(self, posted_event):
        subscribed = {key: value for (key, value) in self._subscribers.items() if value == posted_event.__class__}
        for subscriber in subscribed:
            registrants = filter(lambda r: subscriber.__name__ in dir(r), self._registrants)
            for registrant in registrants:
                threadpool.start(MyRunnable(lambda: subscriber(registrant, posted_event)))

    def register(self, registrant):
        self._registrants.append(registrant)

    def subscribe(self, subscriber, event):
        self._subscribers[subscriber] = event


eventbus = AsyncEventBus()


def subscribe(*args, **kwargs):
    def inner(func):
        event = kwargs['event'] if args[0] is None else args[0]
        eventbus.subscribe(func, event)
        return func

    return inner
