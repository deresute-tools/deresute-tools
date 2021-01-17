from PyQt5.QtCore import QSize, QMimeData, Qt, QPoint
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QComboBox, QAbstractItemView, QApplication

from settings import IMAGE_PATH64, IMAGE_PATH, IMAGE_PATH32
from src import customlogger as logger
from src.db import db
from src.gui.viewmodels.mime_headers import CARD
from src.gui.viewmodels.utils import ImageWidget, NumericalTableWidgetItem
from src.logic.live import Live
from src.logic.profile import card_storage
from src.network import meta_updater
from src.static.skill import SKILL_COLOR_BY_NAME


class CustomCardTable(QTableWidget):
    def __init__(self, *args):
        super().__init__(*args)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.selected = self.selectedItems()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        if self.selectedItems():
            self.selected = self.selectedItems()
        if not self.selected:
            return
        drag = QDrag(self)
        card_row = self.row(self.selected[0])
        card_id = self.item(card_row, 2).text()
        card_img = self.cellWidget(card_row, 1).picture
        mimedata = QMimeData()
        mimedata.setText(CARD + card_id)
        pixmap = QPixmap(card_img.size())
        painter = QPainter(pixmap)
        painter.drawPixmap(0, 0, card_img)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(card_img.size().width() / 2, card_img.size().height() / 2))
        drag.setMimeData(mimedata)
        drag.exec_(Qt.CopyAction | Qt.MoveAction)


class CardView:

    def __init__(self, main):
        self.widget = CustomCardTable(main)
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.setHorizontalScrollMode(1)  # Smooth scroll
        self.widget.setDragEnabled(True)
        self.widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.widget.setSortingEnabled(True)
        self.widget.verticalHeader().setVisible(False)
        self.model = None
        self.size = 20

    def set_model(self, model):
        self.model = model

    def connect_cell_change(self):
        self.widget.cellChanged.connect(lambda r, c: self.model.handle_cell_change(r, c))

    def disconnect_cell_change(self):
        self.widget.cellChanged.disconnect()

    def initialize_pics(self):
        for r_idx in range(self.widget.rowCount()):
            image = ImageWidget(None, self.widget)
            self.widget.setCellWidget(r_idx, 1, image)
        self.connect_cell_change()

    def toggle_auto_resize(self, on=False):
        if on:
            self.widget.horizontalHeader().setSectionResizeMode(4)  # Auto fit
            self.widget.horizontalHeader().setSectionResizeMode(4, 1)  # Auto fit
        else:
            name_col_width = self.widget.columnWidth(4)
            self.widget.horizontalHeader().setSectionResizeMode(0)  # Resize
            self.widget.setColumnWidth(4, name_col_width)

    def load_data(self, data, card_list=None):
        if card_list is None:
            self.widget.setColumnCount(len(data[0]) + 2)
            self.widget.horizontalHeader().setSectionResizeMode(1, 2)  # Not allow change icon column size
            self.widget.setRowCount(len(data))
            self.widget.setHorizontalHeaderLabels(['#', ''] + list(data[0].keys()))
            rows = range(len(data))
        else:
            data_dict = {int(_['ID']): _ for _ in data}
            rows = dict()
            for r_idx in range(self.widget.rowCount()):
                card_id = int(self.widget.item(r_idx, 2).text())
                if card_id not in data_dict:
                    continue
                else:
                    rows[card_id] = r_idx
            rows = [rows[card_id] for card_id in map(int, card_list)]
            data = [data_dict[card_id] for card_id in map(int, card_list)]

        # Turn off sorting to avoid indices changing mid-update
        self.widget.setSortingEnabled(False)
        for r_idx, card_data in zip(rows, data):
            row_count_item = NumericalTableWidgetItem(r_idx + 1)
            row_count_item.setFlags(row_count_item.flags() & ~Qt.ItemIsEditable)
            self.widget.setItem(r_idx, 0, row_count_item)
            for c_idx, (key, value) in enumerate(card_data.items()):
                if isinstance(value, int) and c_idx != 8:
                    item = NumericalTableWidgetItem(value)
                elif value is None:
                    item = QTableWidgetItem("")
                else:
                    item = QTableWidgetItem(str(value))
                if c_idx != 1:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                else:
                    item = QTableWidgetItem()
                    item.setData(Qt.EditRole, value)
                if key == 'Skill':
                    if value is not None:
                        item.setBackground(QColor(*SKILL_COLOR_BY_NAME[value], 135))
                self.widget.setItem(r_idx, c_idx + 2, item)
        logger.info("Loaded {} cards".format(len(data)))
        self.widget.setSortingEnabled(True)
        # Turn on auto fit once to make it look better then turn it off to render faster during resize
        self.toggle_auto_resize(card_list is None)

    def show_only_ids(self, card_ids):
        if not card_ids:
            card_ids = set()
        else:
            card_ids = set(card_ids)
        count = 1
        for r_idx in range(self.widget.rowCount()):
            if int(self.widget.item(r_idx, 2).text()) in card_ids:
                self.widget.setRowHidden(r_idx, False)
                self.widget.item(r_idx, 0).setData(2, str(count))
                count += 1
            else:
                self.widget.setRowHidden(r_idx, True)
        self.refresh_spacing()

    def draw_icons(self, icons, size):
        if size is None:
            self.size = 20
        else:
            self.size = size
        for r_idx in range(self.widget.rowCount()):
            if icons:
                card_id = self.widget.item(r_idx, 2).text()
                self.widget.cellWidget(r_idx, 1).set_path(icons[card_id])
            else:
                self.widget.cellWidget(r_idx, 1).set_path(None)
        self.refresh_spacing()

    def refresh_spacing(self):
        self.widget.verticalHeader().setDefaultSectionSize(self.size + 10)
        self.widget.setColumnWidth(1, self.size + 10)


class CardModel:

    def __init__(self, view):
        assert isinstance(view, CardView)
        self.view = view
        self.images = dict()
        self.owned = dict()

    def attach_calculator_view(self, calculator_view):
        self.calculator_view = calculator_view

    def load_images(self, size=None):
        logger.info("Change card list image size to {}".format(size))
        if size is None:
            self.images = dict()
            self.view.draw_icons(None, size)
            return
        if size is not None:
            assert size == 32 or size == 64 or size == 124
            if size == 32:
                path = IMAGE_PATH32
            elif size == 64:
                path = IMAGE_PATH64
            elif size == 124:
                path = IMAGE_PATH
            for image_path in path.iterdir():
                self.images[image_path.name.split(".")[0]] = image_path
            self.view.draw_icons(self.images, size)

    def initialize_cards(self, card_list=None):
        db.cachedb.execute("""ATTACH DATABASE "{}" AS masterdb""".format(meta_updater.get_masterdb_path()))
        db.cachedb.commit()
        query = """
            SELECT  cdc.id as ID,
                    oc.number as Owned,
                    cdc.name as Name,
                    cc.full_name as Character,
                    REPLACE(UPPER(rt.text) || "+", "U+", "") as Rarity,
                    ct.text as Color,
                    sk.skill_name as Skill,
                    lk.keywords as Leader,
                    sd.condition as Interval,
                    pk.keywords as Prob,
                    CAST(cdc.vocal_max + cdc.bonus_vocal AS INTEGER) as Vocal,
                    CAST(cdc.visual_max + cdc.bonus_visual AS INTEGER) as Visual,
                    CAST(cdc.dance_max + cdc.bonus_dance AS INTEGER) as Dance,
                    CAST(cdc.hp_max + cdc.bonus_hp AS INTEGER) as Life
            FROM card_data_cache as cdc
            INNER JOIN chara_cache cc on cdc.chara_id = cc.chara_id
            INNER JOIN rarity_text rt on cdc.rarity = rt.id
            INNER JOIN color_text ct on cdc.attribute = ct.id
            LEFT JOIN owned_card oc on cdc.id = oc.card_id
            LEFT JOIN masterdb.skill_data sd on cdc.skill_id = sd.id
            LEFT JOIN probability_keywords pk on pk.id = sd.probability_type
            LEFT JOIN skill_keywords sk on sd.skill_type = sk.id
            LEFT JOIN leader_keywords lk on cdc.leader_skill_id = lk.id
        """
        if card_list is not None:
            query += "WHERE cdc.id IN ({})".format(','.join(['?'] * len(card_list)))
            data = db.cachedb.execute_and_fetchall(query, card_list, out_dict=True)
        else:
            data = db.cachedb.execute_and_fetchall(query, out_dict=True)
        db.cachedb.execute("DETACH DATABASE masterdb")
        db.cachedb.commit()
        for card in data:
            if card['Owned'] is None:
                card['Owned'] = 0
            self.owned[int(card['ID'])] = int(card['Owned'])
        self.view.load_data(data, card_list)

    def handle_cell_change(self, r_idx, c_idx):
        if c_idx != 3:
            return
        card_id = int(self.view.widget.item(r_idx, 2).text())
        new_value = self.view.widget.item(r_idx, c_idx).text()
        if str(self.owned[card_id]) == new_value:
            return
        try:
            new_value = int(new_value)
            assert new_value >= 0
        except:
            logger.error("Owned value {} invalid for card ID {}".format(new_value, card_id))
            # Revert value
            self.view.disconnect_cell_change()
            self.view.widget.item(r_idx, c_idx).setData(2, self.owned[card_id])
            self.view.connect_cell_change()
            return
        self.owned[card_id] = new_value
        card_storage.update_owned_cards(card_id, new_value)

    def push_card(self, idx):
        count = 0
        cell_widget = None
        for row in range(self.view.widget.rowCount()):
            if self.view.widget.isRowHidden(row):
                continue
            if count == idx:
                cell_widget = self.view.widget.item(row, 2)
                break
            else:
                count += 1
        if cell_widget is None:
            logger.info("No card at index {}".format(idx))
            return
        self.calculator_view.get_table_view().push_card(int(cell_widget.text()))

    def highlight_event_cards(self, checked):
        highlight_set = Live.static_get_chara_bonus_set(get_name=True)
        for r_idx in range(self.view.widget.rowCount()):
            if self.view.widget.item(r_idx, 5).text() not in highlight_set:
                continue
            for c_idx in range(4,5):
                item = self.view.widget.item(r_idx, c_idx)
                if checked:
                    item.setBackground(QColor(50, 100, 100, 80))
                else:
                    item.setBackground(QColor(0, 0, 0, 0))


class IconLoaderView:
    def __init__(self, main):
        self.widget = QComboBox(main)
        self.widget.setMaximumSize(QSize(1000, 25))

        self.widget.addItem("No icon")
        self.widget.addItem("Small icon")
        self.widget.addItem("Medium icon")
        self.widget.addItem("Large icon")
        self.model = None

    def set_model(self, model):
        assert isinstance(model, IconLoaderModel)
        self.model = model
        self.widget.currentIndexChanged.connect(lambda x: self.trigger(x))

    def trigger(self, idx):
        self.model.load_image(idx)


class IconLoaderModel:
    def __init__(self, view, card_model):
        self.view = view
        self._card_model = card_model

    def load_image(self, idx):
        if idx == 0:
            self._card_model.load_images(size=None)
        elif idx == 1:
            self._card_model.load_images(size=32)
        elif idx == 2:
            self._card_model.load_images(size=64)
        elif idx == 3:
            self._card_model.load_images(size=124)
