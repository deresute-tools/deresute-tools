import unittest

from logic.card import Card
from static.color import Color


class TestCard(unittest.TestCase):
    def test_from_id(self):
        uzu3 = Card.from_id(100448, custom_pots=(0, 0, 0, 0, 0))
        self.assertEqual(uzu3.vo, 6236)
        self.assertEqual(uzu3.da, 4720)
        self.assertEqual(uzu3.vi, 4972)
        self.assertEqual(uzu3.total, 15928)
        self.assertEqual(uzu3.color, Color.CUTE)
        self.assertEqual(str(uzu3), "uzuki3")
