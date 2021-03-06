import atexit
import sys
import traceback

import customlogger as logger
import initializer

logger.log_to_file()


@atexit.register
def main_cleanup():
    logger.info("Virtual Chihiro going to sleep...")


def main():
    logger.info("Starting virtual Chihiro...")

    try:
        initializer.setup(True)
        from gui.main import setup_gui

        app, main = setup_gui(sys.argv)
        main.show()
        app.exec_()
    except:
        logger.critical("ERROR!")
        logger.critical(traceback.print_exc())
