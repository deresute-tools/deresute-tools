import atexit
import sys

import initializer
from src import customlogger as logger

logger.log_to_file()


@atexit.register
def main_cleanup():
    logger.info("Virtual Chihiro going to sleep...")


if __name__ == "__main__":
    logger.info("Starting virtual Chihiro...")

    initializer.setup(True)
    from gui.main import setup_gui

    app, main = setup_gui(sys.argv)
    main.show()
    sys.exit(app.exec_())
