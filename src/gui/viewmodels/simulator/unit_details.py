from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QAbstractItemView, QTableWidgetItem

from db import db
from gui.events.unit_details_events import HookUnitToUnitDetailsEvent, GetSupportLiveObjectEvent
from gui.events.utils import eventbus
from gui.events.utils.eventbus import subscribe
from logic.grandlive import GrandLive
from logic.live import Live
from static.skill import get_sparkle_bonus

HEADERS = [
    "Base Vocal",
    "Base Dance",
    "Base Visual",
    "Base Life",
    "Vocal Motif",
    "Dance Motif",
    "Visual Motif",
    "Life Sparkle SSR",
    "Life Sparkle SR"
]


class UnitDetailsView:
    def __init__(self, main):
        self.main = main
        self.widget = QtWidgets.QTableWidget(main)
        self.widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.widget.setSortingEnabled(False)
        self.widget.verticalHeader().setVisible(True)
        self.widget.horizontalHeader().setVisible(True)
        self.widget.setRowCount(len(HEADERS))
        self.widget.setColumnCount(1)
        self.widget.setVerticalScrollMode(1)  # Smooth scroll
        self.widget.horizontalHeader().setSectionResizeMode(1)
        self.widget.setVerticalHeaderLabels(HEADERS)
        self.widget.setHorizontalHeaderLabels(["Unit"])
        self.widget.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def set_model(self, model):
        self.model = model

    def hook_live(self, live):
        self.model.hook_live(live)


class UnitDetailsModel:
    view: UnitDetailsView

    def __init__(self, view):
        self.view = view
        self.live = None
        eventbus.eventbus.register(self)

    @subscribe(HookUnitToUnitDetailsEvent)
    def hook_live(self, event):
        self.live = eventbus.eventbus.post_and_get_first(GetSupportLiveObjectEvent())
        if self.live.unit is None:
            return
        grand = isinstance(self.live, GrandLive)
        if isinstance(self.live, GrandLive):
            self.view.widget.setColumnCount(3)
            self.view.widget.setHorizontalHeaderLabels(["Unit A", "Unit B", "Unit C"])
        elif isinstance(self.live, Live):
            self.view.widget.setColumnCount(1)
            self.view.widget.setHorizontalHeaderLabels(["Unit"])
        else:
            return

        for c_idx, unit in enumerate(self.live.unit.all_units):
            if grand:
                motif_values = [_[0] for _ in
                                db.masterdb.execute_and_fetchall("SELECT type_01_value FROM skill_motif_value_grand")]
            else:
                motif_values = [_[0] for _ in
                                db.masterdb.execute_and_fetchall("SELECT type_01_value FROM skill_motif_value")]
            vo = int(unit.base_attributes[:5, 0, :].sum())
            vi = int(unit.base_attributes[:5, 1, :].sum())
            da = int(unit.base_attributes[:5, 2, :].sum())
            lf = int(unit.base_attributes[:5, 3, :].sum())
            motif_bonuses = list()
            for appeal in [vo, vi, da]:
                total = appeal // 1000
                if total >= len(motif_values):
                    total = len(motif_values) - 1
                motif_bonuses.append(motif_values[int(total)] - 100)
            trimmed_lf = int(lf // 10)
            sparkle_ssr = get_sparkle_bonus(8, grand)[trimmed_lf] - 100
            sparkle_sr = get_sparkle_bonus(6, grand)[trimmed_lf] - 100

            self.view.widget.setItem(0, c_idx, QTableWidgetItem(str(vo)))
            self.view.widget.setItem(1, c_idx, QTableWidgetItem(str(da)))
            self.view.widget.setItem(2, c_idx, QTableWidgetItem(str(vi)))
            self.view.widget.setItem(3, c_idx, QTableWidgetItem(str(lf)))
            self.view.widget.setItem(4, c_idx, QTableWidgetItem("{}%".format(motif_bonuses[0])))
            self.view.widget.setItem(5, c_idx, QTableWidgetItem("{}%".format(motif_bonuses[2])))
            self.view.widget.setItem(6, c_idx, QTableWidgetItem("{}%".format(motif_bonuses[1])))
            self.view.widget.setItem(7, c_idx, QTableWidgetItem("{}%".format(sparkle_ssr)))
            self.view.widget.setItem(8, c_idx, QTableWidgetItem("{}%".format(sparkle_sr)))
