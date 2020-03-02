import unittest

from src.exceptions import NoLiveFoundException
from src.logic.card import Card
from src.logic.live import Live
from src.logic.unit import Unit
from src.static.song_difficulty import Difficulty


class TestLive(unittest.TestCase):
    def test_master(self):
        c1 = Card.from_query("karen4", custom_pots=(0, 6, 10, 0, 10))
        c2 = Card.from_query("sachiko2", custom_pots=(0, 0, 8, 0, 0))
        c3 = Card.from_query("koume2", custom_pots=(0, 0, 10, 0, 10))
        c4 = Card.from_query("miho4", custom_pots=(0, 4, 10, 0, 10))
        c5 = Card.from_query("fumika1", custom_pots=(0, 6, 10, 0, 0))
        cg = Card.from_query("sae4", custom_pots=(0, 10, 0, 5, 10))
        unit = Unit.from_list([c1, c2, c3, c4, c5, cg])

        live = Live()
        live.set_music("印象", Difficulty.MASTER)
        live.set_unit(unit)
        self.assertEqual(live.get_appeals(), 38965)
        self.assertEqual(live.get_life(), 272)
        self.assertEqual(live.get_support(), 111470)

    def test_mplus(self):
        c1 = Card.from_query("sae4", custom_pots=(10, 10, 10, 10, 10))
        c2 = Card.from_query("chieri2", custom_pots=(10, 10, 10, 10, 10))
        c3 = Card.from_query("chieri2u", custom_pots=(10, 10, 10, 10, 10))
        c4 = Card.from_query("rika4", custom_pots=(10, 10, 10, 10, 10))
        c5 = Card.from_query("yoko1", custom_pots=(10, 10, 10, 10, 10))
        cg = Card.from_query("kaede2", custom_pots=(10, 10, 10, 10, 10))
        unit = Unit.from_list([c1, c2, c3, c4, c5, cg])

        live = Live()
        live.set_music("EVERMORE", Difficulty.MPLUS)
        live.set_unit(unit)
        self.assertEqual(live.get_appeals(), 134140)
        self.assertEqual(live.get_life(), 394)

    def test_music_not_found(self):
        live = Live()
        self.assertRaises(NoLiveFoundException, lambda: live.set_music("印象", Difficulty.TRICK))
        self.assertRaises(NoLiveFoundException, lambda: live.set_music("not found", Difficulty.REGULAR))
