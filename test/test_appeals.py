import unittest

from src.logic.card import Card
from src.logic.live import Live
from src.logic.unit import Unit
from src.simulator import Simulator
from src.static.appeal_presets import APPEAL_PRESETS
from src.static.song_difficulty import Difficulty


class TestAppeal(unittest.TestCase):
    def test_bonus_chara(self):
        sae4 = Card.from_query("sae4", custom_pots=(0, 10, 10, 0, 10))
        chieri4 = Card.from_query("chieri4", custom_pots=(0, 10, 10, 0, 10))
        yoshino3 = Card.from_query("yoshino3", custom_pots=(0, 10, 10, 0, 10))
        rika4 = Card.from_query("rika4", custom_pots=(0, 10, 10, 0, 10))
        mio4 = Card.from_query("mio4", custom_pots=(0, 10, 10, 0, 10))
        kaede2_guest = Card.from_query("kaede2", custom_pots=(10, 10, 10, 0, 0))
        unit = Unit.from_list([sae4, chieri4, yoshino3, rika4, mio4, kaede2_guest])
        live = Live()
        live.set_music(music_name="印象", difficulty=Difficulty.MPLUS)
        live.set_unit(unit)
        sim = Simulator(live)
        sim.simulate()
        self.assertEqual(live.get_appeals(), 155135)
        live.reset_attributes()
        live.set_chara_bonus({262}, 500)
        live.special_option = APPEAL_PRESETS["Event Idols"]
        self.assertEqual(live.get_appeals(), 238635)
        live.reset_attributes()
        live.set_chara_bonus({262}, 5000)
        live.special_option = APPEAL_PRESETS["Event Idols"]
        self.assertEqual(live.get_appeals(), 973137)

    def test_bless1(self):
        c0 = Card.from_query("kaede5", custom_pots=(10, 10, 5, 0, 10))
        c1 = Card.from_query("natalia1", custom_pots=(10, 0, 0, 0, 10))
        c2 = Card.from_query("yoshino3", custom_pots=(0, 10, 10, 0, 10))
        c3 = Card.from_query("sarina1", custom_pots=(0, 0, 0, 0, 0))
        c4 = Card.from_query("shiki3", custom_pots=(10, 0, 10, 0, 10))
        guest = Card.from_query("kaede2", custom_pots=(10, 10, 10, 0, 0))
        unit = Unit.from_list([c0, c1, c2, c3, c4, guest])
        live = Live()
        live.set_music(music_name="印象", difficulty=Difficulty.MPLUS)
        live.set_unit(unit)
        sim = Simulator(live)
        sim._setup_simulator(support=110319)
        self.assertEqual(sim.total_appeal, 279476)

    def test_bless2(self):
        # For some reason, with reso, the other bonuses can only be 0 or -100
        c0 = Card.from_query("kaede5", custom_pots=(10, 10, 5, 0, 10))
        c1 = Card.from_query("sae3", custom_pots=(0, 8, 0, 0, 10))
        c2 = Card.from_query("syuko4", custom_pots=(0, 0, 8, 0, 10))
        c3 = Card.from_query("asuka4", custom_pots=(10, 10, 0, 0, 10))
        c4 = Card.from_query("shiki3", custom_pots=(10, 0, 10, 0, 10))
        guest = Card.from_query("yui2", custom_pots=(10, 10, 10, 0, 0))
        unit = Unit.from_list([c0, c1, c2, c3, c4, guest])
        live = Live()
        live.set_music(music_name="印象", difficulty=Difficulty.MPLUS)
        live.set_unit(unit)
        sim = Simulator(live)
        sim._setup_simulator(support=110319)
        self.assertEqual(sim.total_appeal, 223773)

    def test_bless3(self):
        # For some reason, with reso, the other bonuses can only be 0 or -100
        c0 = Card.from_query("kaede5", custom_pots=(10, 10, 5, 0, 10))
        c1 = Card.from_query("karen4", custom_pots=(0, 6, 10, 0, 10))
        c2 = Card.from_query("syuko4", custom_pots=(0, 0, 8, 0, 10))
        c3 = Card.from_query("asuka4", custom_pots=(10, 10, 0, 0, 10))
        c4 = Card.from_query("shiki3", custom_pots=(10, 0, 10, 0, 10))
        guest = Card.from_query("yui2", custom_pots=(10, 10, 10, 0, 0))
        unit = Unit.from_list([c0, c1, c2, c3, c4, guest])
        live = Live()
        live.set_music(music_name="印象", difficulty=Difficulty.MPLUS)
        live.set_unit(unit)
        sim = Simulator(live)
        sim._setup_simulator(support=110319)
        self.assertEqual(sim.total_appeal, 189565)
