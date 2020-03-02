from PyQt5.QtCore import QMetaObject, QRect, QCoreApplication
from PyQt5.QtGui import QIntValidator, QIcon
from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QMenuBar, \
    QMenu, QStatusBar, QAction, QApplication, QMainWindow, QLineEdit

from main import ROOT_DIR
from src.gui.viewmodels.card import CardView, CardModel, IconLoaderView, IconLoaderModel
from src.gui.viewmodels.quicksearch import QuickSearchView, QuickSearchModel
from src.gui.viewmodels.simulator.wide_smart import MainView, MainModel
from src.gui.viewmodels.song import SongListView, SongListModel, SongView, SongModel
from src.gui.viewmodels.unit import UnitView, UnitModel
from src.logic.profile import profile_manager
from src import customlogger as logger


# noinspection PyAttributeOutsideInit
from src.logic.search import indexer


class UiMainWindow:
    def __init__(self, main):
        self.main = main

    def setup_ui(self):
        logger.info("Initializing UI")
        self.main.resize(1600, 900)
        self.setup_base()
        self.setup_calculator_song_layout()
        self.setup_card_unit_layout()
        self.main.setCentralWidget(self.central_widget)
        self.setup_menu_bar()
        self.retranslate_ui(self.main)
        QMetaObject.connectSlotsByName(self.main)

    def setup_base(self):
        logger.info("Setting up UI base")

        self.central_widget = QWidget(self.main)
        self.grid_layout = QGridLayout(self.central_widget)
        self.main_layout = QVBoxLayout()

    def setup_calculator_song_layout(self):
        logger.info("Setting up calculator and song layouts")

        self.calculator_song_layout = QHBoxLayout()
        self.calculator = QTabWidget(self.central_widget)
        non_grand_tab_view = MainView()
        non_grand_tab_model = MainModel(non_grand_tab_view)
        non_grand_tab_view.set_model(non_grand_tab_model)
        non_grand_tab_view.setup()
        self.grand_tab = QWidget()  # TODO
        self.calculator.addTab(non_grand_tab_view.widget, "WIDE/SMART")
        self.calculator.addTab(self.grand_tab, "GRAND")
        self.calculator_song_layout.addWidget(self.calculator)
        self.song_layout = QVBoxLayout()

        self.import_layout = QHBoxLayout()
        import_text = QLineEdit(self.main)
        import_text.setValidator(QIntValidator(0, 999999999, None))  # Only number allowed
        import_button = QPushButton("Import from ID", self.main)

        def import_from_id():
            profile_manager.import_from_gameid(import_text.text())
            self.card_model.initialize_cards()

        import_button.pressed.connect(lambda: import_from_id())
        self.import_layout.addWidget(import_text)
        self.import_layout.addWidget(import_button)
        self.song_layout.addLayout(self.import_layout)

        song_view = SongView(self.central_widget)
        song_model = SongModel(song_view)
        song_view.set_model(song_model)
        self.song_layout.addWidget(song_view.widget)

        non_grand_tab_view.attach_song_view(song_view)
        song_view.attach_support_model(non_grand_tab_view.support_model)

        song_list_view = SongListView(self.central_widget, song_model)
        song_list_model = SongListModel(song_list_view)
        song_list_view.set_model(song_list_model)
        song_list_model.initialize_songs()
        self.song_layout.addWidget(song_list_view.widget)

        self.calculator_song_layout.addLayout(self.song_layout)
        self.calculator_song_layout.setStretch(0, 0)
        self.calculator_song_layout.setStretch(1, 3)
        self.calculator_song_layout.setStretch(2, 1)
        self.main_layout.addLayout(self.calculator_song_layout)
        self.calculator.setCurrentIndex(0)

    def setup_card_unit_layout(self):
        logger.info("Setting up card and unit layouts")

        self.card_unit_layout = QHBoxLayout()
        self.card_layout = QVBoxLayout()
        self.card_quicksearch_layout = QHBoxLayout()

        self.quicksearch_layout = QHBoxLayout()

        # Set up card MV first
        card_view = CardView(self.central_widget)
        self.card_model = CardModel(card_view)
        card_view.set_model(self.card_model)
        self.card_model.initialize_cards()
        card_view.initialize_pics()
        self.card_layout.addWidget(card_view.widget)

        # Need card view
        quicksearch_view = QuickSearchView(self.central_widget)
        quicksearch_model = QuickSearchModel(quicksearch_view, card_view)
        quicksearch_view.set_model(quicksearch_model)
        self.card_quicksearch_layout.addLayout(self.quicksearch_layout)
        self.quicksearch_layout.addWidget(quicksearch_view.widget)
        quicksearch_model.add_options(self.quicksearch_layout, self.central_widget)

        # Then icon loader MV since it makes use of the card model
        icon_loader_view = IconLoaderView(self.central_widget)
        icon_loader_model = IconLoaderModel(icon_loader_view, self.card_model)
        icon_loader_view.set_model(icon_loader_model)
        icon_loader_view.widget.setToolTip("Larger icons require more RAM to run.")
        icon_loader_model.load_image(0)
        self.card_quicksearch_layout.addWidget(icon_loader_view.widget)
        self.card_layout.addLayout(self.card_quicksearch_layout)

        self.card_layout.setStretch(1, 1)
        self.card_unit_layout.addLayout(self.card_layout)

        self.unit_layout = QVBoxLayout()
        unit_view = UnitView(self.central_widget)
        unit_model = UnitModel(unit_view)
        unit_view.set_model(unit_model)
        unit_model.initialize_units()
        self.unit_layout.addWidget(unit_view.widget)
        self.card_unit_layout.addLayout(self.unit_layout)

        self.add_unit_button = QPushButton()
        self.add_unit_button.setText("Add unit")
        self.add_unit_button.setToolTip(
            "Add an untitled unit. Untitled units are not saved upon exit!\n"
            "Make sure to give your units a name. Unit names must be different.\n"
            "First/Red card is the leader, last/blue card is the guest.")
        self.add_unit_button.clicked.connect(lambda: unit_view.add_empty_widget())
        self.unit_layout.addWidget(self.add_unit_button)

        self.card_unit_layout.setStretch(0, 2)
        self.card_unit_layout.setStretch(1, 1)
        self.main_layout.addLayout(self.card_unit_layout)
        self.grid_layout.addLayout(self.main_layout, 0, 0, 1, 1)

        card_view.toggle_auto_resize(False)

    def setup_menu_bar(self):
        logger.info("Setting up menu bar")

        self.menubar = QMenuBar(self.main)
        self.menubar.setGeometry(QRect(0, 0, 1595, 21))
        self.menuMenu = QMenu(self.menubar)
        self.main.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(self.main)
        self.main.setStatusBar(self.statusbar)
        self.actionExit = QAction(self.main)
        self.menuMenu.addAction(self.actionExit)
        self.menubar.addAction(self.menuMenu.menuAction())

    def retranslate_ui(self, MainWindow):
        _translate = QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("main", "Chihiro"))
        self.menuMenu.setTitle(_translate("main", "Menu"))
        self.actionExit.setText(_translate("main", "Exit"))


def setup_gui(*args):
    app = QApplication(*args)
    app.setApplicationName("Chihiro")
    app.setWindowIcon(QIcon(str(ROOT_DIR / 'icon.png')))
    MainWindow = QMainWindow()
    ui = UiMainWindow(MainWindow)
    ui.setup_ui()
    logger.info("GUI setup successfully")
    return app, MainWindow
