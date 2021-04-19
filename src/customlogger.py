import logging
import threading
from datetime import datetime

from settings import LOGGER_NAME, LOG_DIR

__logger = logging.getLogger(LOGGER_NAME)
__logger.setLevel(logging.DEBUG)

__formatter = logging.Formatter('%(asctime)s - %(threadName)s:%(levelname)s - %(message)s',
                                datefmt='%d-%b-%y %H:%M:%S')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(__formatter)
__logger.addHandler(stream_handler)

mutex = threading.Lock()


def thread_safe(func):
    def wrapper(*args, **kwargs):
        mutex.acquire()
        output = func(*args, **kwargs)
        mutex.release()
        return output

    return wrapper


def print_debug():
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(__formatter)
    __logger.addHandler(stream_handler)


def log_to_file():
    if not LOG_DIR.exists():
        LOG_DIR.mkdir()
    file_handler = logging.FileHandler(LOG_DIR / "{}.log".format(datetime.now().strftime("%Y%m%d-%H%M%S")))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(__formatter)
    __logger.addHandler(file_handler)


@thread_safe
def debug(*args):
    __logger.debug(*args)


@thread_safe
def info(*args):
    __logger.info(*args)


@thread_safe
def warning(*args):
    __logger.warning(*args)


@thread_safe
def error(*args):
    __logger.error(*args)


@thread_safe
def critical(*args):
    __logger.critical(*args)


def setLevel(*args):
    __logger.setLevel(*args)
