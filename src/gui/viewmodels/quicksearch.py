from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QPlainTextEdit, QCheckBox

from logic.search import search_engine
from src import customlogger as logger


class QuickSearchView:
    def __init__(self, main):
        self.widget = QPlainTextEdit(main)
        self.widget.setMaximumSize(QSize(2000, 25))
        self.model = None

    def set_model(self, model):
        assert isinstance(model, QuickSearchModel)
        self.model = model
        self.widget.textChanged.connect(lambda: self.trigger())

    def trigger(self):
        self.model.call_searchengine(self.widget.toPlainText().strip())


class QuickSearchModel:
    def __init__(self, view, card_view):
        self.view = view
        self._card_view = card_view
        self.options = dict()

    def call_searchengine(self, query):
        if query == "" \
                and not self.options["ssr"].isChecked() \
                and not self.options["idolized"].isChecked() \
                and not self.options["owned_only"].isChecked():
            query = "*"
        card_ids = search_engine.advanced_single_query(
            query,
            ssr=self.options["ssr"].isChecked(),
            idolized=self.options["idolized"].isChecked(),
            partial_match=self.options["partial_match"].isChecked(),
            owned_only=self.options["owned_only"].isChecked()
        )
        logger.debug("Query: {}".format(query))
        logger.debug("Result: {}".format(card_ids))
        self._card_view.show_only_ids(card_ids)

    def _add_option(self, option, option_text, parent_layout, main):
        check_box = QCheckBox(main)
        check_box.setText(option_text)
        trigger = lambda: self.call_searchengine(self.view.widget.toPlainText().strip())
        check_box.stateChanged.connect(trigger)
        self.options[option] = check_box
        parent_layout.addWidget(check_box)

    def add_options(self, parent_layout, main):
        for option, option_text in zip(
                ["ssr", "idolized", "owned_only", "partial_match"],
                ["SSR only", "Idolized only", "Owned cards only", "Partial match"]):
            self._add_option(option, option_text, parent_layout, main)
        self.options['ssr'].setToolTip("Only show SSR and SSR+.")
        self.options['idolized'].setToolTip("Only show N+, R+, SR+, and SSR+.")
        self.options['owned_only'].setToolTip("Hide all cards you don't have.")
        self.options['partial_match'].setToolTip("This option might significantly increase query time!")
