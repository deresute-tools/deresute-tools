import unittest

import numpy as np

from logic.unit import Unit
from static.color import Color


class TestSkill(unittest.TestCase):

    def test_duo_ens(self):
        unit = Unit.from_query("kyoko4 uzuki1 kanako1 uzuki3 anzu4 kyoko4")
        np.testing.assert_equal(unit.leader_bonuses(song_color=Color.CUTE),
                                np.array([
                                    [110, 110, 110, 0, 0],
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())
        np.testing.assert_equal(unit.leader_bonuses(song_color=Color.ALL),
                                np.array([
                                    [60, 60, 60, 0, 0],
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())

    def test_single_ens(self):
        unit = Unit.from_query("kyoko4 uzuki1 kanako1 uzuki3 anzu4")
        np.testing.assert_equal(unit.leader_bonuses(song_color=Color.CUTE),
                                np.array([
                                    [55, 55, 55, 0, 0],
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())

    def test_mismatch_ens(self):
        unit = Unit.from_query("kyoko4 uzuki1 kanako1 uzuki3 anzu4 nao4")
        np.testing.assert_equal(unit.leader_bonuses(song_color=Color.CUTE),
                                np.array([
                                    [55, 55, 55, 0, 0],
                                    [30, 30, 30, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())
        np.testing.assert_equal(unit.leader_bonuses(song_color=Color.COOL),
                                np.array([
                                    [30, 30, 30, 0, 0],
                                    [55, 55, 55, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())

    def test_ens_and_princess(self):
        unit = Unit.from_query("kyoko4 uzuki1 kanako1 uzuki3 anzu4 uzuki3")
        np.testing.assert_equal(unit.leader_bonuses(song_color=Color.COOL),
                                np.array([
                                    [80, 80, 80, 0, 0],
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())
        np.testing.assert_equal(unit.leader_bonuses(song_color=Color.CUTE),
                                np.array([
                                    [105, 105, 105, 0, 0],
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())

    def test_duo_princess(self):
        unit = Unit.from_query("uzuki3 uzuki1 kanako1 uzuki3 anzu4 uzuki3")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [100, 100, 100, 0, 0],
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())

    def test_fail_princess(self):
        unit = Unit.from_query("uzuki3 nao4 kanako1 uzuki3 anzu4 uzuki3")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())

    def test_tri_visual(self):
        unit = Unit.from_query("kaede2 nao4 rika4u uzuki3 anzu4 kaede2")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [0, 200, 0, 0, 0],
                                    [0, 200, 0, 0, 0],
                                    [0, 200, 0, 0, 0]
                                ]).transpose())
        unit = Unit.from_query("kaede2 nao4 rika4u uzuki3 anzu4")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [0, 100, 0, 0, 0],
                                    [0, 100, 0, 0, 0],
                                    [0, 100, 0, 0, 0]
                                ]).transpose())

    def test_fail_tri_visual(self):
        unit = Unit.from_query("kaede2 nao4 uzuki1 uzuki3 anzu4")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0]
                                ]).transpose())

    def test_tri_visual_vocal(self):
        unit = Unit.from_query("kaede2 rika4u uzuki1 uzuki3 anzu4 rin2")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [100, 100, 0, 0, 0],
                                    [100, 100, 0, 0, 0],
                                    [100, 100, 0, 0, 0]
                                ]).transpose())

    def test_reso(self):
        unit = Unit.from_query("sae4 rika4u uzuki1 uzuki3 anzu4 kaede2")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [-100, 100, -100, 0, 0],
                                    [-100, 100, -100, 0, 0],
                                    [-100, 100, -100, 0, 0]
                                ]).transpose())

        unit = Unit.from_query("sae4 rika4u rin2 uzuki3 anzu4 kaede2")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [-100, 100, -100, 0, 0],
                                    [-100, 100, -100, 0, 0],
                                    [-100, 100, -100, 0, 0]
                                ]).transpose())
        unit = Unit.from_query("sae4 rika4u kaede2 uzuki3 anzu4 rin2")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [0, 0, -100, 0, 0],
                                    [0, 0, -100, 0, 0],
                                    [0, 0, -100, 0, 0]
                                ]).transpose())

    def test_fail_reso(self):
        unit = Unit.from_query("sae4 rika4u kaede2 yui2 anzu4 rin2")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [100, 0, 0, 0, 0],
                                    [100, 0, 0, 0, 0],
                                    [100, 0, 0, 0, 0]
                                ]).transpose())

    def test_2_reso(self):
        unit = Unit.from_query("sae4 rika4u uzuki1 uzuki3 anzu4 sae4")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [-100, 0, -100, 0, 0],
                                    [-100, 0, -100, 0, 0],
                                    [-100, 0, -100, 0, 0]
                                ]).transpose())

        unit = Unit.from_query("sae4 rika4u uzuki1 uzuki3 anzu4 karen4")
        np.testing.assert_equal(unit.leader_bonuses(),
                                np.array([
                                    [-100, -100, -100, 0, 0],
                                    [-100, -100, -100, 0, 0],
                                    [-100, -100, -100, 0, 0]
                                ]).transpose())
