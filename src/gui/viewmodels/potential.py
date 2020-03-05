from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView, QTableWidgetItem

from settings import IMAGE_PATH32
from src import customlogger as logger
from src.db import db
from src.gui.viewmodels.utils import NumericalTableWidgetItem, ImageWidget
from src.logic.profile import potential


class PotentialView:
    def __init__(self):
        self.parent = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.parent)
        self.widget = QtWidgets.QTableWidget(self.parent)
        self.layout.addWidget(self.widget)
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.setHorizontalScrollMode(1)  # Smooth scroll
        self.widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.widget.setSortingEnabled(True)
        self.widget.verticalHeader().setVisible(False)
        self.widget.verticalHeader().setDefaultSectionSize(75)

    def set_model(self, model):
        self.model = model

    def load_data(self, data):
        self.widget.setColumnCount(len(data[0]))
        self.widget.setRowCount(len(data))
        self.widget.horizontalHeader().setSectionResizeMode(1)
        keys = list(data[0].keys())
        keys[1] = ""
        self.widget.setHorizontalHeaderLabels(keys)
        for r_idx, potential in enumerate(data):
            for c_idx, (key, value) in enumerate(potential.items()):
                if c_idx == 1:
                    item = ImageWidget(None, self.widget)
                    item.set_path(str(IMAGE_PATH32 / "{:06d}.jpg".format(value)))
                    self.widget.setCellWidget(r_idx, c_idx, item)
                    continue
                elif isinstance(value, int):
                    item = NumericalTableWidgetItem(value)
                elif value is None:
                    item = QTableWidgetItem("")
                else:
                    item = QTableWidgetItem(str(value))

                if c_idx in {0, 2, 8}:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                else:
                    item = QTableWidgetItem()
                    item.setData(Qt.EditRole, value)
                self.widget.setItem(r_idx, c_idx, item)
        self.connect_cell_changed()

    def connect_cell_changed(self):
        self.widget.cellChanged.connect(lambda r, c: self.model.handle_cell_change(r, c))

    def disconnect_cell_changed(self):
        self.widget.cellChanged.disconnect()

    def update_total(self, r_idx, total):
        self.widget.item(r_idx, 8).setData(2, total)


class PotentialModel:
    view: PotentialView

    def __init__(self, view):
        self.view = view
        self.potentials = dict()

    def attach_card_model(self, card_model):
        self.card_model = card_model

    def initialize_data(self):
        data = db.cachedb.execute_and_fetchall("""
            SELECT 
                potential_cache.chara_id as ID,
                min(card_data_cache.id) as _card_id,
                chara_cache.full_name as Name,
                potential_cache.vo as Vocal,
                potential_cache.da as Dance,
                potential_cache.vi as Visual,
                potential_cache.li as Life,
                potential_cache.sk as Skill,
                potential_cache.vo+ potential_cache.da+ potential_cache.vi+ potential_cache.li+ potential_cache.sk as Total
            FROM potential_cache
            INNER JOIN chara_cache ON potential_cache.chara_id = chara_cache.chara_id
            INNER JOIN card_data_cache ON card_data_cache.chara_id = potential_cache.chara_id
            GROUP BY card_data_cache.chara_id
        """, out_dict=True)
        for chara in data:
            self.potentials[int(chara['ID'])] = [
                int(chara['Vocal']),
                int(chara['Dance']),
                int(chara['Visual']),
                int(chara['Life']),
                int(chara['Skill'])
            ]
        self.view.load_data(data)

    def handle_cell_change(self, r_idx, c_idx):
        if 3 > c_idx or 7 < c_idx:
            return
        chara_id = int(self.view.widget.item(r_idx, 0).text())
        new_value = self.view.widget.item(r_idx, c_idx).text()
        try:
            new_value = int(new_value)
            assert 0 <= new_value <= 10
        except:
            logger.error("Potential {} invalid for character ID {}".format(new_value, chara_id))
            # Revert value
            self.view.disconnect_cell_changed()
            self.view.widget.item(r_idx, c_idx).setData(2, self.potentials[chara_id][c_idx - 3])
            self.view.connect_cell_changed()
            return
        self.potentials[chara_id][c_idx - 3] = new_value
        # Update
        pots = self.potentials[chara_id].copy()
        # Swap dance / visual
        pots[1] = self.potentials[chara_id][2]
        pots[2] = self.potentials[chara_id][1]
        potential.update_potential(chara_id=chara_id, pots=pots)
        card_ids = db.cachedb.execute_and_fetchall("SELECT id FROM card_data_cache WHERE chara_id = ?", [chara_id])
        card_ids = [_[0] for _ in card_ids]
        self.card_model.initialize_cards(card_ids)
        self.view.update_total(r_idx, sum(pots))
