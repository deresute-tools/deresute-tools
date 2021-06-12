import atexit
import os
import sys
import traceback

from PyQt5.QtWidgets import QApplication

import customlogger as logger
import initializer

logger.log_to_file()


@atexit.register
def main_cleanup():
    logger.info("Virtual Chihiro going back to sleep...")


def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical("ERROR!")
    logger.critical(tb)
    QApplication.quit()


def set_debug_flag():
    if "DEBUG_MODE" not in os.environ:
        os.environ["DEBUG_MODE"] = "0"
        return
    os.environ["DEBUG_MODE"] = "1"


def main():
    logger.info("Starting virtual Chihiro...")
    set_debug_flag()

    sys.excepthook = excepthook
    initializer.setup(True)
    from gui.main import setup_gui

    app, main = setup_gui(sys.argv)
    main.show()
    app.exec_()
