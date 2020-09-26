import logging
from datetime import datetime

from settings import LOGGER_NAME, LOG_DIR

__logger = logging.getLogger(LOGGER_NAME)
__logger.setLevel(logging.DEBUG)

__formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                                datefmt='%d-%b-%y %H:%M:%S')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(__formatter)
__logger.addHandler(stream_handler)


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


def debug(*args):
    __logger.debug(*args)


def info(*args):
    __logger.info(*args)


def warning(*args):
    __logger.warning(*args)


def error(*args):
    __logger.error(*args)


def critical(*args):
    __logger.critical(*args)

def setLevel(*args):
    __logger.setLevel(*args)