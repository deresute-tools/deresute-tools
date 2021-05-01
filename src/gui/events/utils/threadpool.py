from PyQt5.QtCore import QThreadPool

threadpool = QThreadPool()
threadpool.setMaxThreadCount(4)
