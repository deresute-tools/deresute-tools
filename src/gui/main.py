from PyQt5.QtCore import QMetaObject, QRect, QCoreApplication, Qt
from PyQt5.QtGui import QIntValidator, QIcon
from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QMenuBar, \
    QMenu, QStatusBar, QAction, QApplication, QMainWindow, QLineEdit

from chihiro import ROOT_DIR
from src import customlogger as logger
from src.gui.viewmodels.card import CardView, CardModel, IconLoaderView, IconLoaderModel
from src.gui.viewmodels.potential import PotentialView, PotentialModel
from src.gui.viewmodels.quicksearch import QuickSearchView, QuickSearchModel
from src.gui.viewmodels.simulator.wide_smart import MainView, MainModel
from src.gui.viewmodels.song import SongListView, SongListModel, SongView, SongModel
from src.gui.viewmodels.unit import UnitView, UnitModel
from src.logic.profile import profile_manager
from src.logic.search import indexer, search_engine


class CustomMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setui(self, ui):
        self.ui = ui

    def keyPressEvent(self, event):
        key = event.key()
        if QApplication.keyboardModifiers() == Qt.ControlModifier and key == Qt.Key_F:
            self.ui.quicksearch_view.focus()


# noinspection PyAttributeOutsideInit
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
        self.calculator_view = MainView()
        self.calculator_model = MainModel(self.calculator_view)
        self.calculator_view.set_model(self.calculator_model)
        self.calculator_view.setup()
        self.potential_view = PotentialView()
        self.potential_model = PotentialModel(self.potential_view)
        self.potential_view.set_model(self.potential_model)
        self.potential_model.initialize_data()
        self.calculator.addTab(self.calculator_view.widget, "Simulator")
        self.calculator.addTab(self.potential_view.widget, "Potentials")
        self.calculator_song_layout.addWidget(self.calculator)
        self.song_layout = QVBoxLayout()

        self.import_layout = QHBoxLayout()
        self.import_text = QLineEdit(self.main)
        self.import_text.setValidator(QIntValidator(0, 999999999, None))  # Only number allowed
        self.import_button = QPushButton("Import from ID", self.main)
        self.import_button.pressed.connect(lambda: self.import_from_id(self.import_text.text()))
        self.import_layout.addWidget(self.import_text)
        self.import_layout.addWidget(self.import_button)
        self.song_layout.addLayout(self.import_layout)

        self.song_view = SongView(self.central_widget)
        self.song_model = SongModel(self.song_view)
        self.song_view.set_model(self.song_model)
        self.song_layout.addWidget(self.song_view.widget)

        self.song_list_view = SongListView(self.central_widget, self.song_model)
        self.song_list_model = SongListModel(self.song_list_view)
        self.song_list_view.set_model(self.song_list_model)
        self.song_list_model.initialize_songs()
        self.song_layout.addWidget(self.song_list_view.widget)

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
        self.card_view = CardView(self.central_widget)
        self.card_model = CardModel(self.card_view)
        self.card_view.set_model(self.card_model)
        self.card_model.initialize_cards()
        self.card_view.initialize_pics()
        self.card_view.connect_cell_change()
        self.card_layout.addWidget(self.card_view.widget)

        # Need card view
        self.quicksearch_view = QuickSearchView(self.central_widget, self.card_model)
        self.quicksearch_model = QuickSearchModel(self.quicksearch_view, self.card_view)
        self.quicksearch_view.set_model(self.quicksearch_model)
        self.card_quicksearch_layout.addLayout(self.quicksearch_layout)
        self.quicksearch_layout.addWidget(self.quicksearch_view.widget)
        self.quicksearch_model.add_options(self.quicksearch_layout, self.central_widget)

        # Then icon loader MV since it makes use of the card model
        self.icon_loader_view = IconLoaderView(self.central_widget)
        self.icon_loader_model = IconLoaderModel(self.icon_loader_view, self.card_model)
        self.icon_loader_view.set_model(self.icon_loader_model)
        self.icon_loader_view.widget.setToolTip("Larger icons require more RAM to run.")
        self.icon_loader_model.load_image(0)
        self.card_quicksearch_layout.addWidget(self.icon_loader_view.widget)
        self.card_layout.addLayout(self.card_quicksearch_layout)

        self.card_layout.setStretch(1, 1)

        self.unit_layout = QVBoxLayout()
        self.unit_view = UnitView(self.central_widget)
        self.unit_model = UnitModel(self.unit_view)
        self.unit_view.set_model(self.unit_model)
        self.unit_model.initialize_units()
        self.unit_layout.addWidget(self.unit_view.widget)

        self.card_unit_layout.addLayout(self.unit_layout)
        self.card_unit_layout.addLayout(self.card_layout)

        self.add_unit_button = QPushButton()
        self.add_unit_button.setText("Add unit")
        self.add_unit_button.setToolTip(
            "Add an untitled unit. Untitled units are not saved upon exit!\n"
            "Make sure to give your units a name. Unit names must be different.\n"
            "First/Red card is the leader, last/blue card is the guest.")
        self.add_unit_button.clicked.connect(lambda: self.unit_view.add_empty_widget())
        self.unit_layout.addWidget(self.add_unit_button)

        self.card_unit_layout.setStretch(0, 1)
        self.card_unit_layout.setStretch(1, 2)
        self.main_layout.addLayout(self.card_unit_layout)
        self.grid_layout.addLayout(self.main_layout, 0, 0, 1, 1)

        self.card_view.toggle_auto_resize(False)

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

    def import_from_id(self, game_id):
        self.card_view.disconnect_cell_change()
        updated_card_ids = profile_manager.import_from_gameid(game_id)
        if updated_card_ids is None:
            self.card_view.connect_cell_change()
            return
        indexer.im.initialize_index_db(updated_card_ids)
        indexer.im.reindex(updated_card_ids)
        search_engine.engine.refresh_searcher()
        self.card_model.initialize_cards(updated_card_ids)
        self.card_view.connect_cell_change()

    def retranslate_ui(self, MainWindow):
        _translate = QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("main", "Chihiro"))
        self.menuMenu.setTitle(_translate("main", "Menu"))
        self.actionExit.setText(_translate("main", "Exit"))

    def attach(self):
        self.potential_model.attach_card_model(self.card_model)
        self.calculator_view.attach_song_view(self.song_view)
        self.card_model.attach_calculator_view(self.calculator_view)
        self.song_view.attach_support_model(self.calculator_view.support_model)


def setup_gui(*args):
    app = QApplication(*args)
    app.setApplicationName("Chihiro")
    app.setWindowIcon(QIcon(str(ROOT_DIR / 'icon.png')))
    MainWindow = CustomMainWindow()
    ui = UiMainWindow(MainWindow)
    MainWindow.setui(ui)
    ui.setup_ui()
    ui.attach()
    logger.info("GUI setup successfully")
    return app, MainWindow
